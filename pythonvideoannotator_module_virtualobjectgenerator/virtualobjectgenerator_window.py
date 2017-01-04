import pyforms, math, cv2, os
from PyQt4 import QtGui
from pysettings import conf
from pyforms import BaseWidget
from pyforms.Controls import ControlDir
from pyforms.Controls import ControlNumber
from pyforms.Controls import ControlList
from pyforms.Controls import ControlCombo
from pyforms.Controls import ControlSlider
from pyforms.Controls import ControlPlayer
from pyforms.Controls import ControlFile
from pyforms.Controls import ControlText
from pyforms.Controls import ControlButton
from pyforms.Controls import ControlCheckBox
from pyforms.Controls import ControlCheckBoxList
from pyforms.Controls import ControlEmptyWidget
from pyforms.Controls import ControlProgress

from mcvgui.dialogs.simple_filter import SimpleFilter
from mcvapi.blobs.order_by_position import combinations

from pythonvideoannotator_models_gui.dialogs.paths_and_intervals_selector import PathsAndIntervalsSelectorDialog
from pythonvideoannotator_models_gui.dialogs.images_selector import ImagesSelectorDialog
from mcvapi.filters.background_detector import BackgroundDetector

import json

class VirtualObjectGeneratorWindow(BaseWidget):

	def __init__(self, parent=None):
		super(VirtualObjectGeneratorWindow, self).__init__('Virtual object generator', parent_win=parent)
		self.mainwindow = parent

		self.layout().setMargin(5)
		self.setMinimumHeight(400)
		self.setMinimumWidth(400)

		self._panel			= ControlEmptyWidget('Paths')
		self._panel_imgs	= ControlEmptyWidget('Images')

		self._outfile 		= ControlFile('Output file')
		
		self._player 		= ControlPlayer('Player')
		self._progress  	= ControlProgress('Progress')
		self._apply 		= ControlButton('Generate video', checkable=True)

		self._usefixedsize  = ControlCheckBox('Use a fixed size')
		self._usefixedcolor = ControlCheckBox('Use a fixed color')
		self._radius		= ControlSlider('Circle radius', 10, 1, 300)
		self._color			= ControlText('BGR color', '255,255,255')

		
		self._formset = [			
			[
				['_panel','_panel_imgs'],'||','_player',
			],
			('_usefixedsize','_radius', '_usefixedcolor', '_color', ' '),
			'_outfile',
			'_apply',
			'_progress'
		]

		self._panel.value 		= self.paths_dialog  = PathsAndIntervalsSelectorDialog(self)
		self._panel_imgs.value 	= self.images_dialog = ImagesSelectorDialog(self)

		self._apply.value			= self.__apply_event
		self._apply.icon 			= conf.ANNOTATOR_ICON_PATH
		self._outfile.changed_event = self.__outputfile_changed_event
		self._usefixedsize.changed_event = self.__usefixedsize_changed_event
		self._usefixedcolor.changed_event = self.__usefixedcolor_changed_event

		self._player.process_frame_event = self.__player_process_frame_event
		self.paths_dialog.video_selection_changed_event = self.__video_selection_changed_event
		
		self._apply.enabled = False
		self._progress.hide()
		self._radius.hide()
		self._color.hide()

	def init_form(self):
		super(VirtualObjectGeneratorWindow, self). init_form()
		self.paths_dialog.project  = self.mainwindow.project
		self.images_dialog.project = self.mainwindow.project
	
	###########################################################################
	### EVENTS ################################################################
	###########################################################################

	def __usefixedcolor_changed_event(self):
		if self._usefixedcolor.value:
			self._color.show()
		else:
			self._color.hide()

	def __usefixedsize_changed_event(self):
		if self._usefixedsize.value:
			self._radius.show()
		else:
			self._radius.hide()




	def __outputfile_changed_event(self):
		video = self.paths_dialog.current_video
		if video is not None:
			videofilepath, video_extension = os.path.splitext(video.filename)
			outfilepath, outfile_extension = os.path.splitext(self._outfile.value)
			if len(outfilepath)>0:
				self._outfile.value = (outfilepath+video_extension)
				self._apply.enabled = True
			else:
				self._apply.enabled = False
		else:
			self._apply.enabled = False


	def __player_process_frame_event(self, frame):
		paths = self.paths_dialog.paths
		images = self.images_dialog.images
		frame = frame if len(images)!=1 else images[0].image.copy()

		if len(paths)==1:
			index 	 = self._player.video_index
			path  	 = paths[0]
			position = path.get_position(index)
			area  	 = path.get_contour_area_value(index) if not self._usefixedsize.value else (self._radius.value**2*math.pi)
			try:
				color = path.get_color_avg(index) if not self._usefixedcolor.value else tuple(eval(self._color.value))
			except:
				color = 255,255,255

			if position is not None and area is not None and color[0] is not None:
				radius = int(round(math.sqrt(area/math.pi)))				
				cv2.circle(frame, position, radius, color, -1)

		return frame


	def __video_selection_changed_event(self):
		video = self.paths_dialog.current_video
		if video is not None:
			self._player.value = video.video_capture
			if len(self._outfile.value)>0:
				videofilepath, video_extension = os.path.splitext(video.filename)
				outfilepath, outfile_extension = os.path.splitext(self._outfile.value)
				if len(outfilepath)>0:
					self._outfile.value = (outfilepath+video_extension)
					self._apply.enabled = True
				else:
					self._apply.enabled = False

	###########################################################################
	### PROPERTIES ############################################################
	###########################################################################
	
	
	def __update_image_event(self, frame, frame_count):
		self._image.value = frame
		self._progress.value = self._base_nframes + frame_count

	def __apply_event(self):
		ok = True
		
		if len(self.paths_dialog.paths)<1:
			QtGui.QMessageBox.information(self, "Alert", "Please select one path")
			ok = False

		if len(self.paths_dialog.paths)>1 and ok:
			QtGui.QMessageBox.information(self, "Alert", "Please select only one path")
			ok = False

		if len(self.images_dialog.images)>1 and ok:
			QtGui.QMessageBox.information(self, "Alert", "Please select only one image or none")
			ok = False

		if self._apply.checked and ok:
			if len(self.images_dialog.images)==1:
				background = self.images_dialog.images[0].image
			else:
				background = None

			self._panel.enabled 		= False
			self._panel_imgs.enabled 	= False
			self._player.stop()		
			self._player.enabled 		= False
			self._outfile.enabled 		= False	
			self._apply.label 			= 'Cancel'

			for video, (begin,end), paths in self.paths_dialog.selected_data:
				if not self._apply.checked:	break

				self._progress.min = 0
				self._progress.max = (end-begin)
				self._progress.show()
					
				codec = int(video.video_capture.get(cv2.CAP_PROP_FOURCC))
				fps   = int(video.video_capture.get(cv2.CAP_PROP_FPS))

				if background is None:
					size = int(video.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
					capture = video.video_capture
					capture.set(cv2.CAP_PROP_POS_FRAMES, begin)
				else:
					size = background.shape[1], background.shape[0]
					capture = None

				outputvideo = cv2.VideoWriter(self._outfile.value, codec, fps, size)
				try:
					default_color = tuple(eval(self._color.value))
				except:
					default_color = 255,255,255
				default_area = (self._radius.value**2*math.pi)

				for path in paths:
					if not self._apply.checked:	break
					for index in range(int(begin),int(end+1)):
						if not self._apply.checked:	break

						if background is None:
							res, frame = capture.read()
							if not res: break
						else:
							frame = background.copy()

						position = path.get_position(index)
						area 	 = path.get_contour_area_value(index) if not self._usefixedsize.value else default_area
						color = path.get_color_avg(index) if not self._usefixedcolor.value else default_color
						
						if position is not None and area is not None and color[0] is not None:
							radius = int(round(math.sqrt(area/math.pi)))
							cv2.circle(frame, position, radius, color, -1)

						self._progress.value = index					
						outputvideo.write(frame)

				outputvideo.release()

			self._panel.enabled 		= True
			self._panel_imgs.enabled 	= True
			self._player.enabled 		= True
			self._outfile.enabled 		= True
			self._apply.label 			= 'Generate video'
			self._apply.checked 		= False
			self._progress.hide()

			
			




	


if __name__ == '__main__': 
	pyforms.startApp(VirtualObjectGeneratorWindow)
