#!/usr/bin/python3
import os
import re
import PIL
import string
import autopep8
import threading
import numpy as np
import pytesseract  # only needed if want to import from image
import tesseract_ocr  # only needed if want to import from image
from tkinter import *
from tkinter import ttk
from threading import Thread
from inspect import getsourcefile
from subprocess import Popen, PIPE, STDOUT
import tkinter.messagebox,tkinter.filedialog
"""
autopep8
installed by using "pip3 install --upgrade autopep8" in terminal
    need dependency, install by "pip3 install pep8"

pytesseract
installed by using "pip3 install pytesseract" in terminal
    need dependency, install dependency by "brew install tesseract"

tesseract_ocr
installed by using "pip3 install tesseract-ocr" in terminal
    if dependency is needed, install by
    $ brew install --with-libtiff --with-openjpeg --with-giflib leptonica
    $ brew install --devel --all-languages tesseract
"""

################################
# call with larger stack from 
# http://www.cs.cmu.edu/~112/notes/notes-recursion-part2.html#callWithLargeStack
def callWithLargeStack(f,*args):
    import sys
    import threading
    sys.setrecursionlimit(2**14) # max recursion depth of 16384
    isWindows = (sys.platform.lower() in ["win32", "cygwin"])
    if (not isWindows): return f(*args) # sadness...
    threading.stack_size(2**27)  # 64MB stack
    # need new thread to get the redefined stack size
    def wrappedFn(resultWrapper): resultWrapper[0] = f(*args)
    resultWrapper = [None]
    #thread = threading.Thread(target=f, args=args)
    thread = threading.Thread(target=wrappedFn, args=[resultWrapper])
    thread.start()
    thread.join()
    return resultWrapper[0]

################################
# defining Stack class/Exceptions for bracket matching
class EmptyStackError(Exception):
    def __init__(self):
            super().__init__("Stack is empty")

class FullStackError(Exception):
        def __init__(self):
                super().__init__("Stack is full")

class Stack(object):
        def __init__(self, maxSize=100):
            self.maxSize = maxSize
            self.data = []

        def isEmpty(self):
            if self.size() == 0:
                return True
            else:
                return False

        def isFull(self):
            if self.size() == self.maxSize:
                return True
            else:
                return False

        def push(self, data):
            if not self.isFull():
                self.data.append(data)
                return data
            else:
                raise FullStackError()

        def pop(self):
            if not self.isEmpty():
                output = self.data[self.size()-1]
                del self.data[self.size()-1]
                return output
            else:
                raise EmptyStackError()  

        def size(self):
            return len(self.data)

        def peek(self):
            if self.isEmpty():
                raise EmptyStackError
            return self.data[self.size()-1]

        def __iter__(self):
            return iter(self.data)

################################
# UI and init
def run():
    editorName = "Fragments"
    root = Tk()
    root.geometry('1400x600')
    root.title(editorName)
    createSnippetDir()
    initFrames(root)
    initMenuBar(root)
    initTags(root.text)
    keyBindings(root)
    root.time = 0
    recolorizeAll(root.text,root)
    updateLineNumber(root)
    root.words = reservedWords()
    root.listbox = Listbox(root.text)
    root.protocol('WM_DELETE_WINDOW', lambda: exitMessage(root))
    #redirect closing window to a confirmation message
    root.mainloop()

def keyBindings(root):
    #initialize key board shortcuts
    root.text.bind("<KeyRelease>", lambda event: keyRelease(event, root))
    root.text.bind("<KeyPress>", lambda event: keyPressed(event, root))
    root.text.bind('<Command-a>', lambda event: selectAll(root.text,event))
    root.text.bind('<Command-l>', lambda event: selectLine(root.text,event))
    editBindings(root)
    root.bind("<Command-b>",lambda event: executeScript(event,root))
    root.bind("<Command-d>",lambda event: checkStyle(root))
    root.bind("<Command-t>",lambda event: improveStyle(root))
    root.bind("<Command-f>",lambda event: findText(root,event))
    root.bind("<Command-s>",lambda event: saveSnippet(root,event))
    root.bind("<Command-Shift-s>",lambda event: saveScript(root,event))
    root.bind("<Command-w>",lambda event: exitMessage(root,event))
    root.bind("<Command-m>",lambda event: snippetManager(root))
    root.text.bind("<Command-Right>", lambda event: jumpRight(root.text,event))
    root.text.bind("<Command-Left>", lambda event: jumpLeft(root.text,event))
    root.bind("<Command-p>",lambda event: pushMode(root))
    root.bind("<Command-i>",lambda event: addImage(root))

def editBindings(root):
    root.text.bind('<Command-]>', lambda event: indentLine(root.text,event))
    root.text.bind('<Command-[>', lambda event: unindent(root.text,event))
    root.text.bind("<Tab>", lambda event: tab(event,root.text))   
    root.text.bind('<Command-x>', lambda event: cut(root,event))
    root.text.bind('<Command-c>', lambda event: copy(root,event))
    root.text.bind('<Command-v>', lambda event: paste(root,event))
    root.text.bind('<Command-z>', lambda event: undo(root,event))
    root.text.bind("<Command-y>", lambda event: redo(root,event))
    root.text.bind("<Command-/>", lambda event: commentLine(root.text,event))
    root.text.bind("<Command-j>", lambda event: joinLines(root.text,event))
    root.text.bind("<Command-,>", lambda event: addComma(root.text,event))
    selBindings(root)

def selBindings(root):
    text = root.text
    text.bind('<">', lambda event: selComplete(text,event,'"'))
    text.bind("<'>", lambda event: selComplete(text,event,"'"))
    text.bind("<[>", lambda event: selComplete(text,event,"["))
    text.bind("<{>", lambda event: selComplete(text,event,'{'))
    text.bind("<(>", lambda event: selComplete(text,event,'('))

def initMenuBar(root):
    #set up menu bar
    menuBar = Menu(root)
    initFileMenu(menuBar,root)
    initEditMenu(menuBar,root)
    initAboutMenu(menuBar,root)
    root.config(menu=menuBar)
    #end of menu bar

def initFileMenu(menuBar,root):
    fileMenu = Menu(menuBar, tearoff=0)
    fileMenu.add_command(label='Save Snippet', accelerator='Command+S',
                compound='left', underline=0,command=lambda:saveSnippet(root))
    fileMenu.add_command(label='Save Script', accelerator='Shift+Command+S',
                compound='left', underline=0,command=lambda:saveScript(root))
    fileMenu.add_command(label='Manage Snippet', accelerator='Command+M',
                compound='left',underline=0,command=lambda:snippetManager(root))
    fileMenu.add_command(label='Import from Image', accelerator='Command+I',
                compound='left',underline=0,command=lambda:addImage(root))
    fileMenu.add_separator()
    fileMenu.add_command(label='Exit', accelerator='Command+W',
                command=lambda:exitMessage(root))
    menuBar.add_cascade(label='File', menu=fileMenu)

def initEditMenu(menuBar,root):
    editMenu = Menu(menuBar, tearoff=0)
    textCommands(editMenu,root)
    searchAndSelection(editMenu,root)
    lineOperation(editMenu,root)
    menuBar.add_cascade(label='Edit', menu=editMenu)
    pushMenu = Menu(menuBar, tearoff=0)
    pushMenu.add_command(label="Push Mode", accelerator="Command+P",
                compound="left",underline=0,command=lambda:pushMode(root))
    styleMenu = Menu(menuBar, tearoff=0)
    styleMenu.add_command(label="Style Check", accelerator="Command+D",
                compound="left",underline=0,command=lambda:checkStyle(root))
    styleMenu.add_command(label="Improve Style", accelerator="Command+T",
                compound="left",underline=0,command=lambda:improveStyle(root))
    menuBar.add_cascade(label='Push Mode', menu=pushMenu)
    menuBar.add_cascade(label='Check Style', menu=styleMenu)

def textCommands(editMenu,root):
    editMenu.add_command(label='Undo', accelerator='Command+Z', compound='left',
                        command = lambda:undo(root))
    editMenu.add_command(label='Redo', accelerator='Command+Y', compound='left',
                        command = lambda:redo(root))
    editMenu.add_separator()
    editMenu.add_command(label='Cut', accelerator='Command+X', compound='left',
                        command = lambda:cut(root))
    editMenu.add_command(label='Copy', accelerator='Command+C', compound='left',
                        command = lambda:copy(root))
    editMenu.add_command(label='Paste', accelerator='Command+V',compound='left',
                        command = lambda:paste(root))
    editMenu.add_separator()

def searchAndSelection(editMenu,root):
    editMenu.add_command(label='Find', underline=0, accelerator='Command+F',
                        command = lambda:findText(root))
    editMenu.add_separator()
    editMenu.add_command(label='Select All',underline=7,accelerator='Command+A',
                        command = lambda:selectAll(root.text))
    editMenu.add_command(label='Select Line',underline=7,
                accelerator='Command+L',command = lambda:selectLine(root.text))
    editMenu.add_separator()

def lineOperation(editMenu,root):
    editMenu.add_command(label='Indent Line', underline=7, 
        accelerator='Command+]',command = lambda:indentLine(root.text))
    editMenu.add_command(label='Unindent', underline=7, 
        accelerator='Command+[',command = lambda:unindent(root.text))
    editMenu.add_command(label='Comment Line', underline=7, 
        accelerator='Command+/',command = lambda:commentLine(root.text))
    editMenu.add_command(label='Join Line', underline=7, 
        accelerator='Command+j',command = lambda:joinLines(root.text))
    editMenu.add_command(label='Add Comma', underline=7, 
        accelerator='Command+,',command = lambda:addComma(root.text))  

def initAboutMenu(menuBar,root):
    aboutMenu = Menu(menuBar, tearoff=0)
    aboutMenu.add_command(label='About',command = aboutMessage)
    aboutMenu.add_command(label='Key Board Commands',command=keyShortcuts)
    menuBar.add_cascade(label='About', menu=aboutMenu)

def initFrames(root):
    #set different areas, left for file browsing, right for editing
    leftFrame = Frame(root,borderwidth=1, relief="sunken",width = 200)
    rightFrame = Frame(root,borderwidth=1, relief="sunken",width = 1200)
    editorFrame = Frame(root,borderwidth=1, relief="sunken",width = 400)
    resultFrame = Frame(root,borderwidth=1, relief="sunken",width = 600)
    initLineNumberArea(root,editorFrame)
    initMainTextArea(root,editorFrame)
    initResult(root, resultFrame)
    initDirectory(root, leftFrame)
    leftFrame.pack(side = "left", fill = "y", expand = False)
    rightFrame.pack(side = "right", fill = "both", expand = True)
    editorFrame.pack(in_=rightFrame,side = "left", fill = "both",expand = True)
    resultFrame.pack(in_=rightFrame,side = "right", fill = "both",expand=False)
    #end of area setting

def initLineNumberArea(root,editorFrame):
    #set up line number area
    root.lineNumberArea = Canvas(root,width=30,background='gray13')
    root.lineNumberArea.pack(in_=editorFrame,side='left', fill='y')
    #end of line number area

def initResult(root, resultFrame):
    root.result = Text(root, width=40, padx=3, takefocus=0, border=0,
                           background='gray13', state='disabled',
                           foreground = "white", wrap="none")
    root.result.configure(state="normal")
    root.result.insert("1.0","""To Execute Your Script Press Command+B
To Check Your Style Press Command+D""")
    root.result.configure(state="disabled")
    root.resultvsb = Scrollbar(orient="vertical", borderwidth=1,
                            command=root.result.yview)
    root.resulthsb = Scrollbar(orient="horizontal", borderwidth=1,
                            command=root.result.xview)
    root.result.configure(yscrollcommand=root.resultvsb.set)
    root.result.configure(xscrollcommand=root.resulthsb.set)
    root.resultvsb.pack(in_=resultFrame,side='right', fill='y',expand = False)
    root.resulthsb.pack(in_=resultFrame,side='bottom', fill='x',expand = False)
    root.result.pack(in_=resultFrame,side='left', fill='both',expand = True)

def initMainTextArea(root,editorFrame):
    #set up main text area
    textFrame = Frame(borderwidth=1, relief="sunken")
    root.text = Text(background="gray13", foreground = 'white', wrap = "none",
                        borderwidth=0, highlightthickness=0, undo = True,
                        insertbackground = "white")
    #setting up scrollbars for the main text area
    root.vsb = Scrollbar(orient="vertical", borderwidth=1,
                            command=lambda *args: yview(root,*args))
    root.hsb = Scrollbar(orient="horizontal", borderwidth=1,
                            command=root.text.xview)
    root.text.configure(yscrollcommand=root.vsb.set)
    root.text.configure(xscrollcommand=root.hsb.set)
    root.vsb.pack(in_=textFrame,side="right", fill="y", expand=False)
    root.hsb.pack(in_=textFrame,side="bottom", fill="x", expand=False)
    root.text.pack(in_=textFrame, side="left", fill="both", expand=True)
    textFrame.pack(in_=editorFrame,side="right", fill="both", expand=True)
    initCursorLabel(root,root.text)
    #end of main text area

def initCursorLabel(root,text):
    (row,col) = (root.text.index("insert").split(".")[0],
                root.text.index("insert").split(".")[1])
    root.cursorLabel=Label(text,
                        text='Line: {0} | Column: {1}'.format(row,col))
    root.cursorLabel.pack(expand='no',fill='none',side='right',anchor='se')

def yview(root,*args):
    root.text.yview(*args)
    updateLineNumbers(root)

################################
# browsing/searching snippet
def initDirectory(root, leftFrame):
    searchFrame = Frame(leftFrame,relief="sunken")
    treeFrame = Frame(leftFrame,relief="sunken")
    root.treeview = ttk.Treeview(treeFrame)
    initTreeview(root.treeview,root)
    ttk.Style().configure("Treeview", background="grey13", 
             foreground="white", fieldbackground="grey13")
    root.fileSearch = Entry(searchFrame)
    root.fileSearch.pack(side='right')
    root.fileSearch.bind("<KeyRelease>",lambda event:
        searchSnippet(root.fileSearch.get(),root.treeview,root,event))
    Label(searchFrame, text="Search:",underline=0).pack(side="left")
    searchFrame.pack(side='top',fill='x')
    treeFrame.pack(side="bottom",fill='both',expand=True)
    treesb = Scrollbar(orient="vertical",borderwidth=1,
                                    command=root.treeview.yview)
    root.treeview.configure(yscrollcommand=treesb.set)
    treesb.pack(in_=treeFrame,side='right',fill='y',expand=False)
    root.treeview.pack(side="left",fill = 'both', expand=True)

def initTreeview(treeview,root):
    treeview.delete(*treeview.get_children())
    currentPath = os.path.dirname(os.path.abspath(
                                            getsourcefile(lambda:None)))
    snippetDir = os.path.join(currentPath,"snippetDir")
    for tag in os.listdir(snippetDir):
        if os.path.isdir(os.path.join(snippetDir,tag)):
            node = treeview.insert('','end',text = tag,open=True)
            for snippet in os.listdir(os.path.join(snippetDir,tag)):
                if "snippet" in snippet:
                    treeview.insert(node,'end',text = snippet.split('.')[0],
                    tags = str(os.path.join(snippetDir,tag,snippet)))
    treeview.bind("<Double-1>", lambda event:
                                openSnippet(treeview,root,event))

def openSnippet(treeview,root,event):
    try:
        itemId = treeview.selection()[0]
        fileName = treeview.item(itemId)['tags'][0]
        content = readFile(fileName)
        root.text.insert(END,content)
        recolorize(root.text)
        return "break"
    except:
        return "break"

def searchSnippet(fileName,treeview,root,event=None):
    if fileName == '':
        initTreeview(treeview,root)
    else:
        treeview.delete(*treeview.get_children())
        currentPath = os.path.dirname(os.path.abspath(
                                                getsourcefile(lambda:None)))
        snippetDir = os.path.join(currentPath,"snippetDir")
        for tag in os.listdir(snippetDir):
            if os.path.isdir(os.path.join(snippetDir,tag)):
                for snippet in os.listdir(os.path.join(snippetDir,tag)):
                    if fileName.lower() in snippet.split('.')[0].lower():
                        treeview.insert('','end',text = snippet.split('.')[0],
                            tags = str(os.path.join(snippetDir,tag,snippet)))
        treeview.bind("<Double-1>", lambda event:
                                    openSnippet(treeview,root,event))

def keyRelease(event, root):
    #check max character, recolorize current line, and add comments
    if event.keysym == "Return":
        addTab(root.text)
    maxCharCheck(root.text)
    colorizeLine(root.text,root.text.index(INSERT).split('.')[0])
    callWithLargeStack(addComment,root.text)
    updateLineNumbers(root)
    scriptParsing(root.text.get("1.0", "insert wordstart"),root)
    giveSuggestion(root)
    if int(root.text.index("end").split('.')[0]) < 200:
        checkBracket(root.text)
    else:
        start = root.text.index("insert linestart")
        end = root.text.index("insert lineend")
        checkBracket(root.text,start,end)
    root.time = 0

def keyPressed(event,root):
    if event.keysym == "BackSpace":
        deleteTab(root.text)

def deleteTab(text):
    line = int(text.index(INSERT).split(".")[0])
    if text.get("insert -3c","insert") == "   ":
        text.delete("insert -3c","insert")

def addTab(text):
    #if the statements that need indentation is detected indent automatically
    line = int(text.index(INSERT).split(".")[0])
    spaceNumber = 0
    indentWords = ["def","class","if","elif","else",
                    "try","except","for","while"]
    indent = False
    lineStart,lineEnd = "{0}.0".format(line-1),"{0}.end".format(line-1)
    for word in indentWords:
        if text.search(word,lineStart,stopindex=lineEnd):
            indent = True 
    if indent == True:
        text.insert("{0}.0".format(line),"    ")
    for c in text.get(lineStart,lineEnd):
        if c == " ":
            spaceNumber += 1
        else:
            break
    text.insert("{0}.0".format(line),spaceNumber * " ")

################################
# line number/cursor
def updateLineNumber(root,event=None):
    updateLineNumbers(root)
    updateCursor(root)
    root.lineCallback = root.text.after(100,updateLineNumber,root)

def updateLineNumbers(root,event=None):
    root.lineNumberArea.delete(ALL)
    for line in range(1,int(root.text.index("end").split('.')[0])):
        try:
            x = root.text.bbox("{0}.0".format(line))[0]
            y = root.text.bbox("{0}.0".format(line))[1]
            root.lineNumberArea.create_text(30/2,y,anchor='n',
                        text = str(line),fill = "white",font = "Times 13")
        except:
            pass

def updateCursor(root):
    (row,col) = (root.text.index("insert").split(".")[0],
                root.text.index("insert").split(".")[1])
    cursorPosition = 'Line: {0} | Column: {1}'.format(row,col)
    root.cursorLabel.config(text = cursorPosition)

def initTags(text):
    text.tag_configure("exceed", underline = True)
    text.tag_configure("definition",foreground = "#64d6eb")
    text.tag_configure("statement",foreground = "#f92672")
    text.tag_configure("value",foreground = "#ae81ff")
    text.tag_configure("string",foreground = "#d7cc6c")
    text.tag_configure("comment",foreground = "#75715e")
    text.tag_configure("openBracket", background = "red")

def maxCharCheck(text):
    #check if a line has over 80 characters, if over 80, underline 
    maxC = 80
    for line in range(1, int(text.index('end').split('.')[0])):
        if int(text.index("{0}.end".format(line)).split('.')[1]) > maxC:
            text.tag_remove("exceed","{0}.0".format(line),"{0}.80".format(line))
            text.tag_add("exceed","{0}.80".format(line),"{0}.end".format(line))
        else:
            text.tag_remove("exceed","{0}.0".format(line),"{}.end".format(line))

################################
# editing features
def selectAll(text,event=None):
    text.tag_add(SEL, "1.0", "end -1c")
    text.mark_set(INSERT, "1.0")
    text.see(INSERT)
    return "break"

def selectLine(text,event=None):
    text.tag_add(SEL,"insert linestart","insert lineend")
    text.mark_set(INSERT, "insert linestart")
    text.see(INSERT)
    return "break"

def indentLine(text,event=None):
    try:
        startLine = int(text.index("sel.first").split('.')[0])
        endLine = int(text.index("sel.last").split('.')[0])+1
        for line in range(startLine,endLine):
            text.insert("{0}.0".format(line),"    ")
    except:
        line = int(text.index(INSERT).split('.')[0])
        text.insert("{0}.0".format(line),"    ")
    return "break"

def unindent(text,event=None):
    try:
        startLine = int(text.index("sel.first").split('.')[0])
        endLine = int(text.index("sel.last").split('.')[0])+1
        for line in range(startLine,endLine):
            if text.get("{0}.0".format(line),"{0}.4".format(line)) == "    ":
                text.delete("{0}.0".format(line),"{0}.4".format(line))
    except:
        line = int(text.index(INSERT).split('.')[0])
        if text.get("{0}.0".format(line),"{0}.4".format(line)) == "    ":
            text.delete("{0}.0".format(line),"{0}.4".format(line))
    return "break"

#use multiple thread to speed up the comment process
def commentLine(text,event=None):
    try:
        startLine = int(text.index("sel.first").split('.')[0])
        endLine = int(text.index("sel.last").split('.')[0])+1
        if endLine - startLine > 2:
            difference = endLine - startLine
            Thread(target = doComment,args=(text,startLine,
                startLine+difference//2)).start()
            Thread(target = doComment,args=(text,startLine+difference//2,
                endLine)).start()
        else:
            doComment(text,startLine,endLine)
    except:
        line = int(text.index(INSERT).split('.')[0])
        doComment(text,line,line+1)
    return "break"

def doComment(text,startLine,endLine):
    for line in range(startLine,endLine):
        if text.get("{}.0".format(line)) == "#":
            text.delete("{}.0".format(line))
        else:
            text.insert("{}.0".format(line),"#")
    recolorize(text)

def tab(event,text):
    text.insert(INSERT, " " * 4)
    return 'break'

def cut(root,event=None):
    root.text.event_generate("<<Cut>>")
    updateLineNumbers(root)
    return "break"

def copy(root,event=None):
    root.text.event_generate("<<Copy>>")
    return "break"

def paste(root,event=None):
    root.text.event_generate("<<Paste>>")
    recolorize(root.text)
    updateLineNumbers(root)
    return "break"

def undo(root,event=None):
    root.text.event_generate("<<Undo>>")
    updateLineNumbers(root)
    return "break"

def redo(root,event=None):
    root.text.event_generate("<<Redo>>")
    updateLineNumbers(root)
    return 'break'

################################
# text searching/replacing
def findText(root,event=None):
    searchWindow = initSearchWindow(root)
    textToSearch = Entry(searchWindow, width=25)
    textToSearch.grid(row=0, column=1, padx=2, pady=2, sticky='we')
    textToReplace = Entry(searchWindow, width=25)
    textToReplace.grid(row=1,column=1, padx=2,pady=2, sticky='we')
    textToSearch.focus_set()
    case = IntVar()
    Checkbutton(searchWindow, text='Ignore Case', variable=case).grid(
        row=3, column=1, sticky='e', padx=2, pady=2)
    Button(searchWindow, text="Find All", underline=0, command=lambda: 
            searchResult(textToSearch.get(), case.get(),
            root.text, searchWindow, textToSearch)
            ).grid(row=0, column=2, sticky='e' + 'w', padx=2, pady=2)
    Button(searchWindow, text="Replace All", underline=0, command=lambda:
            replaceAll(textToSearch.get(), case.get(),root.text,
                textToReplace.get())).grid(row=1, column=2,sticky='e'+'w',
                padx=2,pady=2)
    searchWindow.protocol('WM_DELETE_WINDOW', 
                            lambda: closeSearchWindow(root.text,searchWindow))
    return "break"

def initSearchWindow(root):
    searchWindow = Toplevel(root)
    searchWindow.title('Find Text')
    searchWindow.transient(root)
    searchWindow.resizable(False, False)
    Label(searchWindow, text="Find All:").grid(row=0, column=0, sticky='e')
    Label(searchWindow, text="Replace:").grid(row=1, column=0,sticky='e')
    return searchWindow

def closeSearchWindow(text,searchWindow):
    text.tag_remove('match', '1.0', END)
    searchWindow.destroy()

def searchResult(word, case, text, searchWindow, textToSearch):
    text.tag_remove('match', '1.0', END)
    matchNumber = 0
    if word:
        startIndex = '1.0'
        while True:
            startIndex = text.search(word,startIndex,nocase=case,stopindex=END)
            if not startIndex:
                break
            endIndex = '{}+{}c'.format(startIndex, len(word))
            text.tag_add('match', startIndex, endIndex)
            matchNumber += 1
            startIndex = endIndex
        text.tag_config('match', foreground='grey13', background='yellow')
    textToSearch.focus_set()
    searchWindow.title('{} matches found'.format(matchNumber))

def replaceAll(word, case, text,replaceWord):
    if word and replaceWord:
        startIndex = "1.0"
        while True:
            startIndex = text.search(word, startIndex,
                                    nocase=case, stopindex=END)
            if not startIndex:
                break
            endIndex = '{}+{}c'.format(startIndex, len(word))
            text.delete(startIndex,endIndex)
            text.insert(startIndex, replaceWord)
            startIndex = endIndex
        tkinter.messagebox.showinfo(title="Replace Done",
            message = "All '{0}' are replaced with '{1}'".format(word,
                                                                replaceWord))
    else:
        tkinter.messagebox.showinfo(title="Replace Error",
            message = "Fill in both blanks!") 

################################
# executing script

# file I/O from
# http://www.cs.cmu.edu/~112/notes/notes-strings.html#basicFileIO
def readFile(path):
    with open(path, "rt") as f:
        return f.read()

def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)
# end of file I/O

def executeScript(event, root):
    # use subprocess to get the executed result and display in the frame
    refreshResult(root)
    script = root.text.get("1.0",END)
    writeFile("FragmentsTemp.py",script)
    filePath = os.path.abspath("FragmentsTemp.py")
    cmd = 'python3 {0}'.format(filePath)
    cmdResult = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE,
                    stderr=STDOUT, close_fds=True)
    output = cmdResult.stdout.read().decode("UTF-8")
    refreshResult(root,output)

def refreshResult(root,output = ''):
    root.result.config(state = "normal")
    root.result.delete('1.0', 'end')
    root.result.insert('1.0',output)
    root.result.config(state = "disabled")


################################
# saving
def saveScript(root,event=None):
    fileName = tkinter.filedialog.asksaveasfilename(defaultextension=".py", 
        filetypes=[("Python Documents", "*.py")])
    if fileName:
        content = root.text.get("1.0","end")
        writeFile(fileName,content)
        tkinter.messagebox.showinfo("Saved!","Your script is saved!")
    initTreeview(root.treeview,root)
    return "break"

def saveSnippet(root,event=None):
    saveWindow = Toplevel(root)
    saveWindow.title("Save Snippet")
    saveWindow.transient(root)
    saveWindow.resizable(False, False)
    Label(saveWindow, text="Snippet Name").grid(row=0, column=0, sticky='e')
    snippetName = Entry(saveWindow, width=25)
    snippetName.grid(row=0, column=1, padx=2, pady=2, sticky='we')
    Label(saveWindow, text="Tag").grid(row=1, column=0, sticky='e')
    snippetTag = Entry(saveWindow, width=25)
    snippetTag.grid(row=1, column=1, padx=2, pady=2, sticky='we')
    snippetName.focus_set()
    Button(saveWindow, text="Save Snippet", underline=0, command=lambda: 
            saveSnippetResult(snippetName.get(),root.text,snippetTag.get(),root)
            ).grid(row=0, column=2, sticky='e' + 'w', padx=2, pady=2)
    return "break"

def saveSnippetResult(name,text,tag,root):
    if name and tag:
        currentPath = os.path.dirname(os.path.abspath(
                                                getsourcefile(lambda:None)))
        snippetDir = os.path.join(currentPath,"snippetDir")
        absName = os.path.join(snippetDir,tag,name + ".snippet")
        name = name+".snippet"
        if absName in listFiles(snippetDir):
            replace = tkinter.messagebox.askyesno(title="Snippet Already Exist",
            message = "Snippet already exist, do you want to replace it?")
            if replace == True:
                saveFile(text,absName,root)
                tkinter.messagebox.showinfo("Saved!","Your snippet is saved!")
        else:
            if not os.path.exists(os.path.join(snippetDir,tag)):
                os.makedirs(os.path.join(snippetDir,tag))
            saveFile(text,absName,root)
            tkinter.messagebox.showinfo("Saved!","Your snippet is saved!")
    else:
        tkinter.messagebox.showinfo("Error!","Fill both name and tag!")

def saveFile(text,absName,root):
    content = text.get("1.0","end")
    writeFile(absName,content)
    initTreeview(root.treeview,root)

def listFiles(path):
    if os.path.isfile(path):
        return [path]
    else:
        files = []
        for fileName in os.listdir(path):
            files += listFiles(os.path.join(path,fileName))
        return files

def createSnippetDir():
    currentPath = os.path.dirname(os.path.abspath(getsourcefile(lambda:None)))
    if not os.path.exists(os.path.join(currentPath,"snippetDir")):
        os.makedirs(os.path.join(currentPath,"snippetDir"))

def aboutMessage(event=None):
    tkinter.messagebox.showinfo(title="About Fragments",
        message="Fragment Snippet Editor\nDeveloped by Guodong Zhao")

def exitMessage(root,event=None):
    if tkinter.messagebox.askokcancel("Are you sure you want to quit?",
            "Make sure to save the snippets or script before exit."):
        root.text.after_cancel(root.callback)
        root.text.after_cancel(root.lineCallback)
        root.destroy()

################################
# syntax highlighting
def recolorize(text):
    for line in range(1, int(text.index('end').split('.')[0])):
        colorizeLine(text,line)
    callWithLargeStack(addComment,text)
    tripleQuote(text)
    lineMax = 200
    if int(text.index("end").split(".")[0]) < lineMax:
        checkBracket(text)
    else:
        start = text.index("insert linestart")
        end = text.index("insert lineend")
        checkBracket(text,start,end)

def tripleQuote(text):
    #check for triple quotes in the text
    content = text.get("1.0","end")
    unbalanced,start,triples = 0,0,[]
    for i in range(len(content)-len("''")):
        if unbalanced == 0:
            if content[i:i+len("'''")] == "'''":
                unbalanced = 1
                unmatched = "'''"
                start = i
            elif content[i:i+len('"""')] == '"""':
                unbalanced = 1
                unmatched = '"""'
                start = i
        else:
            if content[i:i+len("'''")] == unmatched:
                unbalanced,unmatched = 0,""
                end = i + len("'''")
                triples.append((start,end))
    if unbalanced == 1: triples.append((start,len(content)))
    addTriple(text,triples,content)

#add tags to the triple quotes identified
def addTriple(text,triples,content):
    for (start,end) in triples:
        string = content[start:end]
        index = text.search(string,"1.0",stopindex="end")
        text.tag_add("string",index,"{0} +{1}c".format(index,len(string)))

def recolorizeAll(text,root):
    recolorize(text)
    delay = 4000
    root.time += delay
    root.callback = text.after(delay,recolorizeAll,text,root)

def colorizeLine(text,line):
    content = text.get("{0}.0".format(line),"{0}.end".format(line))
    addTags(lineParsing(content),text,line)

#recursively colorize commented lines
def addComment(text,startIndex = "1.0"):
    startIndex = text.search("#", startIndex,stopindex=END)
    if not startIndex:
        return None
    endIndex = '{0}.end'.format(startIndex.split(".")[0])
    if "string" not in text.tag_names(startIndex):
        clearTagsRange(text,startIndex,endIndex)
        text.tag_add("comment",startIndex,endIndex)
    addComment(text,endIndex)

#analyze a line into its parts and describe their syntactic roles.
def lineParsing(s):
    (parsed,word,unbalanced,possible) = initParsing()
    for c in s:
        if unbalanced != 0:
            word += c
            if c == quotation:
                parsed.append(word)
                word,unbalanced,quotation = "",0,None
        elif c in possible:
            word += c
        else:
            if word: parsed.append(word)
            word = ""
            if c in ["'",'"']:
                quotation = "'" if c == "'" else '"'
                unbalanced += 1
                word += c
            else:
                parsed.append(c)
    if word: parsed.append(word)
    return parsed

def initParsing():
    possible = set([c for c in string.ascii_letters+string.digits])
    (parsed,word,unbalanced) = ([],"",0)
    return (parsed,word,unbalanced,possible)

#add tags to the parsed parts according to their syntactic role
def addTags(parsed,text,line,index=0):
    clearLineTags(text,line)
    definition,statement,value = initWords()
    for word in parsed:
        if word in definition:
            text.tag_add("definition","{0}.{1}".format(line,index),
                        "{0}.{1}".format(line,index+len(word)))
        elif word in statement:
            text.tag_add("statement","{0}.{1}".format(line,index),
                        "{0}.{1}".format(line,index+len(word)))
        elif word in value or isNumber(word):
            text.tag_add("value","{0}.{1}".format(line,index),
                        "{0}.{1}".format(line,index+len(word)))
        else:
            try:
                if type(eval(word)) == str:
                    text.tag_add("string","{0}.{1}".format(line,index),
                                "{0}.{1}".format(line,index+len(word)))
            except:
                pass
        index += len(word)

def isNumber(word):
    for c in word:
        if c not in string.digits:
            return False
    return True

#clears tags from beginning to end
def clearLineTags(text,line):
    text.tag_remove("definition","{0}.0".format(line),"{0}.end".format(line))
    text.tag_remove("statement","{0}.0".format(line),"{0}.end".format(line))
    text.tag_remove("value","{0}.0".format(line),"{0}.end".format(line))
    text.tag_remove("string","{0}.0".format(line),"{0}.end".format(line))
    text.tag_remove("comment","{0}.0".format(line),"{0}.end".format(line))
    text.tag_remove("openBracket","{0}.0".format(line),"{0}.end".format(line))

#clears tags in a certain range
def clearTagsRange(text,startIndex,endIndex):
    text.tag_remove("definition",startIndex,endIndex)
    text.tag_remove("statement",startIndex,endIndex)
    text.tag_remove("value",startIndex,endIndex)
    text.tag_remove("string",startIndex,endIndex)
    text.tag_remove("comment",startIndex,endIndex)
    text.tag_remove("openBracket",startIndex,endIndex)

def initWords():
    definition = set(["def", "class", "lambda", "abs", "dict", "help", "min", 
            "setattr", "all", "dir ", "hex ", "next", "slice", "any ", 
            "divmod", "id", "object", "sorted", "ascii", "enumerate", 
            "input", "oct", "staticmethod", "bin", "eval", "int", 
            "open", "str", "bool", "isinstance ", "ord", "sum", 
            "bytearray", "filter", "issubclass ", "pow", "super", 
            "bytes", "float", "iter", "tuple", "callable", "format", 
            "len", "property", "type", "chr", "frozenset", "list", 
            "range", "vars", "classmethod", "getattr", "locals", 
            "repr", "zip", "compile ", "globals", "map", "reversed", 
            "complex", "hasattr", "max", "round", "delattr", 
            "hash", "memoryview", "set"])
    statement = set(["print", "exec", "and", "or", "not", "<", ">",
            "=", "!", "is", "in", "*", "/", "-", "+",
            "|", "^", "%", "~","from","import","return",
            "assert", "pass", "del", "yield", "raise", "break", 
            "continue", "global", "nonlocal","for","while","if","else",
            "try","except","finally","with","elif"])
    value = set(["None", "True", "False", "NotImplemented", "Ellipsis"])
    return definition,statement,value

################################
# line operations
def joinLines(text,event=None):
    try:
        startLine = int(text.index("sel.first").split('.')[0])
        endLine = int(text.index("sel.last").split('.')[0])
        content = ""
        for line in range(startLine,endLine+1):
            content += text.get("{0}.0".format(line),"{0}.end".format(line))
        text.delete("{0}.0".format(startLine),"{0}.end".format(endLine))
        text.insert("{0}.0".format(startLine),content)
    except:
        pass
    return  "break"

def addComma(text,event=None):
    try:
        startLine = int(text.index("sel.first").split('.')[0])
        endLine = int(text.index("sel.last").split('.')[0])+1
        for line in range(startLine,endLine):
            text.insert("{0}.end".format(line),",")
    except:
        line = int(text.index(INSERT).split('.')[0])
        text.insert("{0}.end".format(line),",")
    return "break"

def jumpRight(text,event=None):
    line = int(text.index(INSERT).split('.')[0])
    text.mark_set("insert","{0}.end".format(line))
    text.see("insert")
    return "break"

def jumpLeft(text,event=None):
    line = int(text.index(INSERT).split('.')[0])
    text.mark_set("insert","{0}.0".format(line))
    text.see("insert")
    return "break"

def selComplete(text,event,add):
    other = {'"':'"',"'":"'","[":"]","{":"}","(":")"}
    try:
        text.insert("sel.first",add)
        text.insert("sel.last",other[add])
        return "break"
    except:
        pass

def keyShortcuts():
    shortcuts = """
Command+a: Select All\nCommand+l: Select Line
Command+b: Run Code\nCommand+f: Find/Replace
Command+s: Save Snippet\nCommand+i: Import from Image
Command+Shift+s: Save Script\nCommand+w: Exit
Command+Right: Jump to line end\nCommand+Left: Jump to line startIndex
Command+]: Indent Line\nCommand+[: Unindent Line
Command+/: Comment Line\nCommand+j: Join Line
Command+z/y: Undo/Redo\nCommand+g: Confirm suggestion
Command+,: Add comma to every line\nCommand+d: Check Style
Command+t: Correct Style
"""
    tkinter.messagebox.showinfo(title="Keyboard shortcuts for Fragments",
        message=shortcuts)

################################
# autoComplete suggestion

# parse a script to get the variable names,function names etc.
def scriptParsing(s,root):
    (parsed,word,unbalanced,possible) = initParsing()
    for c in s:
        if unbalanced != 0:
            word += c
            if c == quotation:
                word,unbalanced,quotation = "",0,None
        elif c in possible:
            word += c
        else:
            if word and len(word) > 3:
                parsed.append(word)
            word = ""
            if c in ["'",'"']:
                quotation = "'" if c == "'" else '"'
                unbalanced += 1
                word += c
    root.words = set(parsed)
    root.words.update(reservedWords())

#give suggestion based on the parsed script and the current word
def giveSuggestion(root):
    root.listbox.destroy()
    current = root.text.get("insert-1c wordstart","insert-1c wordend")
    possibleWords = []
    for word in root.words:
        if len(current) > 1: possibleWords = fuzzyMatch(current,root.words)
    root.listbox = ttk.Treeview(root.text,selectmode="browse")
    if possibleWords:
        for item in possibleWords:
            root.listbox.insert("","end",text = item,tags= item)
        if root.text.bbox("insert-1c"):
            bx,by,width,height = root.text.bbox("insert-1c")
            width,height,maximum = 7,15,360
            length = root.listbox.winfo_reqheight()
            by = by - length - height if by > maximum else by
            root.listbox.place(x=bx+width,y=by+height)
            root.bind("<Command-g>",lambda event: confirmFirst(root))
            root.listbox.bind("<<TreeviewSelect>>", lambda event:
                                                    confirmSelection(root))
    else:
        root.listbox.destroy()

#use regular expression to do fuzzy mathcing when looking for suggestions
def fuzzyMatch(current, words):
    possibleWords = []
    #conver the current word to regular expression
    #for example: convert "fuzzy" to "f.*?u.*?z.*?z.*?y"
    #here I use lazy(.*?) instead of greedy(.*) to achieve the desired rank
    pattern = '.*?'.join(current)
    regex = re.compile(pattern,re.IGNORECASE) #compile regex, ignoring case
    for word in words:
        match = regex.search(word)
        if match and word != current:
            possibleWords.append((len(match.group()), match.start(), word))
    #here I am using a list of tuples containing the length of matching,
    #the starting of the match, and the matched word to store the result
    #By doing this we can return the words in the order that exact matches
    #appears in the front of the list
    return [x for _, _, x in sorted(possibleWords)]

def confirmSelection(root):
    try:
        itemId = root.listbox.selection()[0]
        word = root.listbox.item(itemId)['tags'][0]
        root.listbox.destroy()
        root.text.delete("insert-1c wordstart","insert")
        root.text.insert("insert",word+' ')
        root.text.focus_set()
        root.unbind("<Command-g>")
        return "break"
    except:
        return "break"

def confirmFirst(root):
    try:
        root.listbox.selection_set(root.listbox.get_children()[0])
        return "break"
    except:
        pass

def reservedWords():
    length = 3
    words = set()
    for i in range(length):
        for c in initWords()[i]:
            if len(c) >= length:
                words.add(c)
    return words

################################
# snippet manager
def snippetManager(root):
    height,width = 600,600
    manager = Toplevel(root,height=height,width=width)
    manager.title('Snippet Manager: Double Click to delete Snippet')
    manager.transient(root)
    manager.minsize(height,width)
    manager.maxsize(height,width)
    managerTree = ttk.Treeview(manager)
    initManager(managerTree,root)
    managersb = Scrollbar(manager,orient="vertical",borderwidth=1,
                                    command=managerTree.yview)
    managerTree.configure(yscrollcommand=managersb.set)
    managersb.pack(side='right',fill='y',expand=False)
    managerTree.pack(side="left",fill = 'both', expand=True)

def initManager(managerTree,root):
    managerTree.delete(*managerTree.get_children())
    currentPath = os.path.dirname(os.path.abspath(getsourcefile(lambda:None)))
    snippetDir = os.path.join(currentPath,"snippetDir")
    for tag in os.listdir(snippetDir):
        if os.path.isdir(os.path.join(snippetDir,tag)):
            node = managerTree.insert('','end',text = tag,open=True)
            for snippet in os.listdir(os.path.join(snippetDir,tag)):
                managerTree.insert(node,'end',text = snippet.split('.')[0],
                    tags = str(os.path.join(snippetDir,tag,snippet)))
    managerTree.bind("<Double-1>", lambda event:
                                deleteSnippet(managerTree,root,event))

def deleteSnippet(managerTree,root,event=None):
    try:
        itemId = managerTree.selection()[0]
        fileName = managerTree.item(itemId)['tags'][0]
        if tkinter.messagebox.askokcancel("Delete Snippet?",
            "Do you want to delete {0}?".format(fileName)):
            os.remove(fileName)
            initTreeview(root.treeview,root)
            initManager(managerTree,root)
        return "break"
    except:
        return "break"

################################
# bracket check

# loop through the text once and mark the unbalanced brackets using
# the Stack defined earlier. Takes time of O(n).
def checkBracket(text,start="1.0",end="end"):
    text.tag_remove("openBracket",start,end)
    content,stack,pairing,reverse = initBracket(text,start,end)
    for i in range(len(content)): #loop through text
        if ("string" not in text.tag_names("{0} +{1}c".format(start,i))
            and "comment" not in text.tag_names("{0} +{1}c".format(start,i))):
            #only check for brackets out of strings
            current = text.get("{0} +{1}c".format(start,i))
            if current in pairing: #if current is start of bracket
                stack.push((current,i)) #push into stack
            elif current in reverse: #if it is close bracket
                if stack.isEmpty():
                    #it is a unbalanced bracket if there is no start bracket
                    text.tag_add("openBracket","{0} +{1}c".format(start,i))
                else:
                    #check for matching bracket
                    if stack.peek()[0] != reverse[current][0]:
                        text.tag_add("openBracket","{0} +{1}c".format(start,i))
                    else:
                        stack.pop()
    #tag brackets if there are still brackets unmatched
    if not stack.isEmpty():
        for (c,i) in stack:
            text.tag_add("openBracket","{0} +{1}c".format(start,i))

def initBracket(text,start="1.0",end="end"):
    content = text.get(start,end)
    stack = Stack()
    pairing = {"[":"]","{":"}","(":")"}
    reverse = dict()
    for key in pairing:
        reverse[pairing[key]] = key
    return content,stack,pairing,reverse

################################
# push mode
def pushMode(root):
    tkinter.messagebox.showinfo(title="Enter Push Mode",
            message = """Entering Push Mode:
In push mode, you will set a time you want to code.
You have to keep coding in this time. 
If idle time is longer than 4 seconds, 
your last line of code will disappear.""")
    pushTimeWindow(root)

def pushTimeWindow(root):
    pushWindow = Toplevel(root)
    pushWindow.title("How long do you want to code?")
    pushWindow.transient(root)
    pushWindow.resizable(False,False)
    Label(pushWindow,text="""You Will Be Pushed To Code In Push Mode
Enter the time you want to code in minutes:
(Non integer input will result in 10 minutes of coding)""").grid(
                row=0,column=0,sticky='n')
    timeEntry = Entry(pushWindow,width=25)
    timeEntry.grid(row=1,column=0,sticky='n')
    timeEntry.focus_set()
    Button(pushWindow,text="Start Pushing",underline=0,command=lambda:
    enterPush(root,timeEntry.get(),pushWindow)).grid(row=2,column=0,sticky='n')

def enterPush(root,maxTime,pushWindow):
    pushWindow.destroy()
    try:
        maxTime = int(maxTime)
    except:
        maxTime = 10
    root.text.configure(undo=False)
    root.unbind("<Command-p>")
    root.time = 0
    seconds = 60
    root.count = 0
    root.progressBar = ttk.Progressbar(root.text,orient=HORIZONTAL, 
        length=200,mode='determinate',maximum=maxTime*60,value = root.count)
    root.progressBar.place(x=root.text.winfo_width()//2,y=0,anchor="n")
    deleteLast(root.text,root,maxTime)

#delete the last line of code if idle time is longer than 4 seconds
def deleteLast(text,root,maxTime=10):
    root.progressBar.configure(value = root.count)
    delay,checkTime,seconds = 1000,4000,60
    if root.time > checkTime:
        text.delete("end -1c linestart","end")
    root.count += 1
    root.pushCallback = text.after(delay,deleteLast,text,root,maxTime)
    if root.count >= maxTime*seconds:
        text.after_cancel(root.pushCallback)
        exitPush(root)

def exitPush(root):
    tkinter.messagebox.showinfo(title="Exit Push Mode",
            message = "Push Mode Time Up!")
    root.progressBar.destroy()
    root.text.configure(undo=True)
    root.bind("<Command-p>",lambda event: pushMode(root))

################################
# read from image
def addImage(root):
    img = tkinter.filedialog.askopenfilename(
        title = "Choose an image to open",
        filetypes = (("jpeg files","*.jpg"),("png files","*.png"),
                    ("gif files","*.gif")))
    indentation = processImg(img)
    try:
        code=processCode(pytesseract.image_to_string(PIL.Image.open(
                            "ocrTemp.jpg"),lang="eng"),indentation)
        root.text.insert(END,code)
        recolorize(root.text)
    except UnicodeDecodeError:
        try:
            code = processCode(tesseract_ocr.text_for_filename(
                                "ocrTemp.jpg"),indentation)
            root.text.insert(END,code)
            recolorize(root.text)
        except:
            print(sys.exc_info())
            tkinter.messagebox.showinfo(title="Error",
                message = "Sorry, Fragments Cannot recognize your image.")

def processCode(code,indentation):
    result,indent = "",0
    indentation = [] if indentation == None else indentation
    if len(indentation) == len(code.splitlines()):
        for i in range(len(indentation)):
            result += indentation[i]*" "+code.splitlines()[i]+"\n"
    else:
        for i in range(len(code.splitlines())):
            currentLine = code.splitlines()[i]
            if (("def " in currentLine) or 
                ("if " in currentLine and "elif" not in currentLine) or 
                ("try:" in currentLine and "except " not in currentLine)):
                result += "    "*indent + currentLine + "\n"
                indent += 1
            elif (("elif " in currentLine) or ("else" in currentLine) or 
                "finally " in currentLine):
                indent -= 1
                result += "    "*indent + currentLine + "\n"
                indent += 1
            else:
                result += "    "*indent + currentLine + "\n"
    return autopep8.fix_code(result)

def processImg(img,indent=None):
    color = PIL.Image.open(img)
    gray = color.convert('L')
    bw = gray.point(lambda x: 0 if x<128 else 255, '1') #conver into b/w img
    width,height = bw.size
    if height < 500:
        #conver image into list expression
        lst = list(bw.getdata())
        lst = [lst[i:i+width] for i in range(0, len(lst), width)]
        #identify the start of each row of pixel, calculate the average start  
        # point to get the indentation level of the line
        indent,currentBlock,blankLines = [],[],0
        for i in range(len(lst)):
            try:
                currentBlock.append(lst[i].index(0))
                blankLines = 0
            except:
                blankLines += 1
            if blankLines > 4 and len(currentBlock) > 5:
                indent.append(calculateIndentation(currentBlock))
                blankLines,currentBlock = 0,[]
        indent = recalculateIndent(indent)
    bw.save("ocrTemp.jpg")
    return indent

def calculateIndentation(currentBlock):
    stdDev = np.std(currentBlock)
    mean = np.mean(currentBlock)
    processedBlock = []
    #delete the outliers
    for n in currentBlock:
        if abs(n - mean) <= stdDev:
            processedBlock.append(n)
    #calculate the indentation level
    return (sum(processedBlock)//len(processedBlock))

def recalculateIndent(indent):
    temp = []
    result = []
    for n in indent:
        temp.append(n-min(indent))
    for n in temp:
        result.append(round(n/10))
    return result

################################
# style check
def checkStyle(root):
    # use subprocess to get the result of style check
    refreshResult(root)
    script = root.text.get("1.0",END)
    writeFile("FragmentsTemp.py",script)
    filePath = os.path.abspath("FragmentsTemp.py")
    cmd = 'pep8 --first {0}'.format(filePath)
    cmdResult = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE,
                    stderr=STDOUT, close_fds=True)
    output = cmdResult.stdout.read().decode("UTF-8")
    output = output.replace("{}:".format(filePath),"")
    output = output + """\n\nUse Command+T to automatically improve your style.
Use Command+B to run your code."""
    refreshResult(root,output)

def improveStyle(root):
    refreshResult(root)
    script = root.text.get("1.0",END)
    improved = autopep8.fix_code(script)
    root.text.delete("1.0","end")
    root.text.insert("1.0",improved)
    recolorize(root.text)

if __name__ == "__main__":
    run()