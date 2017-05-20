from Tkinter import *
from tkFileDialog import askopenfilename, askdirectory
import ttk

class StartupWindow(Frame):
	def browse(self,target,version):
		if version == 'input':
			feedback = askopenfilename(filetypes=[('CSV Files','.csv')])
		elif version == 'output':
			feedback = askdirectory()

		target['textvariable'] = feedback
		target.delete(0,END)
		target.insert(0,feedback)
		target.xview_moveto(1)

	def runProcess(self,position):
		if self.FILE_ENTRY['textvariable'] != 'PY_VAR0' and self.OUTPUT_FOLDER_ENTRY['textvariable'] != 'PY_VAR1':
			self.quit()

	def changeButtonName(self):
		if self.run_version.get() == 1:
			self.PROCESS_BUTTON["text"] = "Get Records"
		else:
			self.PROCESS_BUTTON["text"] = "Fix Authorities"

	def createWidgets(self,master):
		f1 = Frame(master,width=600,height=250)
		f1.pack()

		Label(f1,text="Select CSV file of names to fix:").grid(row=0,column=0,padx=2,pady=2,sticky='w')

		self.FILE_ENTRY = Entry(f1,width=50,textvariable=self.filepath)
		self.FILE_ENTRY.grid(row=1,column=0,padx=2,pady=2,sticky='w',columnspan=25)

		self.INPUT_BROWSE = Button(f1,command= lambda: self.browse(self.FILE_ENTRY,'input'))
		self.INPUT_BROWSE["text"] = "Browse"
		self.INPUT_BROWSE.grid(row=1,column=25,padx=2,pady=2,sticky='w',columnspan=1)

		Label(f1,text="Select ouptut folder:").grid(row=2,column=0,padx=2,pady=2,sticky='w')

		self.OUTPUT_FOLDER_ENTRY = Entry(f1,width=50,textvariable=self.output_folder)
		self.OUTPUT_FOLDER_ENTRY.grid(row=3,column=0,padx=2,pady=2,sticky='w',columnspan=25)

		self.OUTPUT_BROWSE = Button(f1,command= lambda: self.browse(self.OUTPUT_FOLDER_ENTRY,'output'))
		self.OUTPUT_BROWSE["text"] = "Browse"
		self.OUTPUT_BROWSE.grid(row=3,column=25,padx=2,pady=2,sticky='w',columnspan=1)

		f2 = Frame(master,width=600,height=250)
		f2.pack()

		self.PROCESS_BUTTON = Button(f2,command= lambda position=f2: self.runProcess(position))
		self.PROCESS_BUTTON["text"] = "Fix Authorities"

		self.VERSION_CHECKBOX = Checkbutton(f1,text="Retrieve problematic records without fixing them",variable=self.run_version,onvalue=1,offvalue=0,command= lambda: self.changeButtonName())
		self.VERSION_CHECKBOX.grid(row=4,column=0,padx=2,pady=15,sticky='w',columnspan=1)

		self.PROCESS_BUTTON.grid(row=5,column=1,padx=20,pady=5,columnspan=1)

	def __init__(self,master=None):
		Frame.__init__(self,master)
		self.filepath = StringVar()
		self.output_folder = StringVar()
		self.run_version = BooleanVar()
		self.pack()
		self.createWidgets(master)

class ProgressBar(Frame):
	def createWidgets(self,master,size_of_task):
		f1 = Frame(master,width=600,height=250,bg="#ececec")
		f1.pack()

		self.LABEL = Label(f1,text="Percent of Records Processed:",bg="#ececec").grid(row=0,column=0,padx=2,pady=2,sticky='w')

		self.PROGRESS_BAR = ttk.Progressbar(f1,orient=HORIZONTAL,length=400,mode='determinate',maximum=size_of_task,variable=self.number_complete)
		self.PROGRESS_BAR.grid(row=1,column=0,padx=5,pady=5,sticky='w')

	def updateProgress(self):
		self.number_complete.set(self.number_complete.get() + 1)
		self.update_idletasks()
		self.update()

	def __init__(self,size_of_task,master=None):
		Frame.__init__(self,master)
		self.number_complete = DoubleVar()
		self.number_complete.set(0)
		self.pack()
		self.createWidgets(master,size_of_task)

def showProgress(size_of_task):
	root = Tk()
	root.title('Fix Authorities')
	root.geometry("598x150")
	root.configure(background="#ececec")

	progress = ProgressBar(size_of_task,master=root)
	return progress, root

def startGUI():
	root = Tk()
	root.title('Fix Authorities')
	root.geometry("598x220")
	
	app = StartupWindow(master=root)
	app.mainloop()
	return app.FILE_ENTRY['textvariable'], app.OUTPUT_FOLDER_ENTRY['textvariable'], (not app.run_version.get()), root