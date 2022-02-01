
import numpy as np
import PyQt5.QtWidgets as QW
import PyQt5.QtGui as QG
import PyQt5.QtCore as QC
from PyQt5.QtCore import Qt,pyqtSignal,pyqtSlot
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.bezier as bz
from collections.abc import Iterable

import os,sys,re

qt_css="""
QWidget
{
    font-size:20pt;
    font-family:"Times New Roman", Times, serif;
}
"""


xs = np.r_[1,0,1,2,0,1,2,0,1,2]
ys = np.r_[-1,2,2,2,1,1,1,0,0,0]
ps = np.c_[xs,ys]

control_point_indices = {
    (0,) :  [7,8,5,6],
    (1,) :  [7,8,5],
    (2,) :  [7,8,5,4],
    (3,) :  [8,9,6,5,8],
    (4,) :  [7,9,3,1,7,9],
    (0,1) : [6,5,2],
    (0,2) : [6,4],
    (0,3) : [6,5,8],
    (0,4) : [6,5,8,9],
    (1,2) : [2,5,4],
    (1,3) : [5,0],
    (1,4) : [5,8,9],
    (2,3) : [4,5,8],
    (2,4) : [4,5,8,9],
    (3,4) : [0,8,9],
}

def keys_from_number(number: int):
    stops = tuple(np.argwhere(np.array(list(bin(number)[2:][::-1]))=="1")[:,0])
    return [stops[:1]]+[(p0,p1) for p0,p1 in zip(stops[:-1],stops[1:])]

def plot_number(ax,number,**prop):
    dx = prop.pop("dx",0)
    dy = prop.pop("dy",0)
    N = prop.pop("N",100)
    if number == 0:
        return
    keys = keys_from_number(number)
    shifted_ps = ps+np.asarray((dx,dy))[None,:]
    for key in keys:
        cps_indices = control_point_indices[key]
        bezier_curve = bz.BezierSegment(shifted_ps[cps_indices])
        t = np.linspace(0,1,N)
        curve = bezier_curve(t)
        if key==(1,):
            curve = np.vstack((curve,shifted_ps[2:3]))
        elif key[0]==1 and key[1] in (3,4):
            curve = np.vstack((shifted_ps[2:3],curve))
        if key in ((3,),(4,)):
            curve = np.vstack((shifted_ps[7:8],curve))
        if key[-1]==3:
            curve = np.vstack((curve,shifted_ps[:1]))
        ax.plot(*curve.T,'k-')

def draw_plus(x,y,ax):
    ax.plot([x-0.2,x+0.2],[y,y],"k",lw=2)
    ax.plot([x,x],[y-0.2,y+0.2],"k",lw=2)

def draw_minus(x,y,ax):
    ax.plot([x-0.2,x+0.2],[y,y],"k",lw=2)

def draw_times(x,y,ax):
    ax.plot([x-0.2,x+0.2],[y-0.2,y+0.2],"k",lw=2)
    ax.plot([x+0.2,x-0.2],[y-0.2,y+0.2],"k",lw=2)

def draw_equals(x,y,ax):
    ax.plot([x-0.2,x+0.2],[y+0.1,y+0.1],"k",lw=2)
    ax.plot([x-0.2,x+0.2],[y-0.1,y-0.1],"k",lw=2)


draw_sign = {"+":draw_plus,"-":draw_minus,"*":draw_times,"=":draw_equals}

class Numbers(QW.QMainWindow):
    def __init__(self):
        super().__init__()
        self.center_widget = QW.QWidget()
        self.setCentralWidget(self.center_widget)
        layout = QW.QVBoxLayout(self.center_widget)
        panel=QW.QGroupBox("Evaluate Expression")
        panel_layout=QW.QHBoxLayout(panel)
        label=QW.QLabel("Input: ")
        panel_layout.addWidget(label)
        
        self.edit=QW.QLineEdit()
        self.edit.setAlignment(Qt.AlignTop)
        panel_layout.addWidget(self.edit)

        layout.addWidget(panel)

        self.canvas=FigureCanvas(Figure())
        layout.addWidget(self.canvas)
        self.canvas.setSizePolicy(QW.QSizePolicy.Expanding, QW.QSizePolicy.Expanding)
        
        self.edit.textChanged.connect(self.draw)
        
        self.ax=self.canvas.figure.add_axes([0,0,1,0.95])
        self.ax.set_ylim([-1.5,2.5])
        self.ax.set_frame_on(False)

    def draw_one(self,index,pos,text,ncols):
        sign=""
        DY=-4*(index//ncols)
        if str(text)[0] in "-+*=":
            sign,text=text[0],text[1:]
            draw_sign.get(sign,lambda *args:())(pos-0.5,DY+0.5,self.ax)
        try:
            hex_vals=hex(int(text))[2:]
            first=0 if len(hex_vals)==1 else int(hex_vals[0],16)<2
        except:
            return index,pos
        
        self.ax.plot([pos],[DY],'o',color='k')
        self.ax.text(pos,DY+2.1,f"0x{hex_vals}={int(hex_vals,16)}",ha="left",va="bottom")
        gridwidth=2*(len(hex_vals)-first)
        self.ax.vlines(range(pos,pos+gridwidth+1),DY-1,DY+2,color='gray',lw=1)
        self.ax.hlines([DY-1,DY,DY+1,DY+2],pos,pos+gridwidth,color='gray',lw=1)
        for hex_pos,val in enumerate(hex_vals[::-1]):
            rv=int(val,16)
            if hex_pos==len(hex_vals)-2:
                nv=int(hex_vals[0],16)
                if nv==1:
                    plot_number(self.ax,rv+16*(nv!=16),N=800,color="k",dx=pos,dy=DY)
                    pos+=2
                    break
            plot_number(self.ax,rv+16*(hex_pos<len(hex_vals)-1),N=800,color="k",dx=pos,dy=DY)
            pos+=2
        return index+1,pos

    def draw(self,text):
        pos=0
        try:
            exprs=eval(text)
            texts=text.split(",")
        except Exception as e:
            return
        self.ax.clear()
        if not isinstance(exprs, Iterable):
            exprs=[exprs]
        if len(texts)<len(exprs):
            texts=map(str,exprs)
        j=0
        maxx=2
        ncols=8 if len(exprs)<41 else 16
        for index,(text,raw) in enumerate(zip(exprs,texts)):
            if index==128:
                break
            if j//ncols>(j-1)//ncols:
                pos=0
            parts=[""]
            for r in raw:
                if r in "+-*" and len(parts[-1])>0:
                    parts.append("")
                parts[-1]=parts[-1]+r
            if len(parts)>1:
                for p in parts:
                    j,pos=self.draw_one(j,pos,p,ncols)
                    pos+=1
                text="="+str(text)
            j,pos=self.draw_one(j,pos,text,ncols)
            pos+=1
            maxx=max(pos,maxx)
            
        self.ax.set_xlim([-0.5,pos+0.5])
        self.ax.set_ylim([-1.1,2.5])
        self.ax.axis("equal")
        self.canvas.draw()


if __name__=="__main__":
    app=QW.QApplication([])

    app.setApplicationName("Bihex Generator")
    app.setStyleSheet(qt_css)
        
    numbers=Numbers()
    numbers.show()
    
    sys.exit(app.exec_())