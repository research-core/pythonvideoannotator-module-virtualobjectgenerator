import pyforms, math, cv2, os

from pysettings import conf
from pyforms import BaseWidget
from pyforms.Controls import ControlDir
from pyforms.Controls import ControlNumber
from pyforms.Controls import ControlList
from pyforms.Controls import ControlToolBox
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

from pythonvideoannotator_models_gui.dialogs import DatasetsDialog
from pythonvideoannotator_models_gui.dialogs import ImagesDialog
from mcvapi.filters.background_detector import BackgroundDetector
from pythonvideoannotator_models_gui.models.video.objects.object2d.datasets.contours import Contours
from pythonvideoannotator_models_gui.models.video.objects.object2d.datasets.path import Path
from pythonvideoannotator_models_gui.models.video.objects.object2d.datasets.value import Value

import simplejson as  json

if conf.PYFORMS_USE_QT5:
	from PyQt5 import QtGui
else:
	from PyQt4 import QtGui



class VirtualObjectGeneratorWindow(BaseWidget):

	def __init__(self, parent=None):
		super(VirtualObjectGeneratorWindow, self).__init__('Virtual object generator', parent_win=parent)
		self.mainwindow = parent

		if conf.PYFORMS_USE_QT5:
			self.layout().setContentsMargins(5,5,5,5)
		else:
			self.layout().setMargin(5)
		self.setMinimumHeight(400)
		self.setMinimumWidth(400)

		self._toolbox = ControlToolBox('Tool')

		self._panel_path	= ControlEmptyWidget('Set the object path',  DatasetsDialog(self) )
		self._panel_area	= ControlEmptyWidget('Set the object area', DatasetsDialog(self) )
		self._panel_colors  = ControlEmptyWidget('Set the object color', DatasetsDialog(self) )
		self._panel_imgs	= ControlEmptyWidget('Set the video background', ImagesDialog(self)   )
		
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
				'_toolbox','||','_player',
			],
			'_outfile',
			'_apply',
			'_progress'
		]

		self._panel_path.value.datasets_filter   = lambda x: isinstance(x, (Contours, Path) )
		#self._panel_area.value.datasets_filter   = lambda x: isinstance(x, Value )
		self._panel_colors.value.datasets_filter = lambda x: isinstance(x, (Contours, Path) ) and hasattr(x, 'has_colors_avg') and x.has_colors_avg

		self._toolbox.value = [
			('PATH',
				[self._panel_path]										), 
			('AREA (optional)',
				[self._panel_area,(self._usefixedsize, self._radius)]	),
			('COLOR (optional)',
				[self._panel_colors,(self._usefixedcolor, self._color) ]),
			('BACKGROUND (optional)',
				[self._panel_imgs]										)
		]

		self._apply.value			= self.__apply_event
		self._apply.icon 			= conf.ANNOTATOR_ICON_PATH
		self._outfile.changed_event = self.__outputfile_changed_event
		self._usefixedsize.changed_event = self.__usefixedsize_changed_event
		self._usefixedcolor.changed_event = self.__usefixedcolor_changed_event
		
		self._player.process_frame_event = self.__player_process_frame_event

		self._panel_path.value.video_selection_changed_event = self.__video_selection_changed_event
		
		self._apply.enabled = False
		self._progress.hide()
		self._radius.hide()
		self._color.hide()
	
	###########################################################################
	### EVENTS ################################################################
	###########################################################################

	def __usefixedcolor_changed_event(self):
		if self._usefixedcolor.value:
			self._color.show()
			self._panel_colors.hide()
		else:
			self._color.hide()
			self._panel_colors.show()


	def __usefixedsize_changed_event(self):
		if self._usefixedsize.value:
			self._radius.show()
			self._panel_area.hide()
		else:
			self._radius.hide()
			self._panel_area.show()

	def __outputfile_changed_event(self):
		video = self._panel_path.value.selected_video
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


	def __get_object_area(self, path, areas, index):
		try:
			if self._usefixedsize.value:
				area = (self._radius.value**2*math.pi)
			elif len(areas)>0:
				a = areas[0]
				if isinstance(a, Value ):
					area = a.get_value(index)
				else:
					area = a.get_area_value(index)				
			else:
				area = path.get_area_value(index)
			if area is None: raise Exception()
		except:
			area = 30**2*math.pi
		return area


	def __get_object_color(self, path, colors, index):
		try:
			if self._usefixedcolor.value:
				color = tuple(eval(self._color.value))
			elif len(colors)>0:
				color = colors[0].get_color_avg(index)				
			else:
				color = path.get_color_avg(index)
			if color is None: raise Exception()
		except:
			color = 255,255,255
		return color


	def __player_process_frame_event(self, frame):
		paths  = self._panel_path.value.datasets
		areas  = self._panel_area.value.datasets
		colors = self._panel_colors.value.datasets
		images = self._panel_imgs.value.images

		frame  = frame if len(images)!=1 else images[0].image.copy()

		index  = self._player.video_index-1				
		for path in paths:
			position 	= path.get_position(index)
			area 		= self.__get_object_area(path, areas, index)			
			color 		= self.__get_object_color(path, colors, index)

			if position is not None and area is not None and color is not None:
				radius = int(round(math.sqrt(area/math.pi)))				
				cv2.circle(frame, position, radius, color, -1)

		return frame


	def __video_selection_changed_event(self):
		video = self._panel_path.value.selected_video
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
		
		if len(self._panel_path.value.datasets)<1:
			QtGui.QMessageBox.information(self, "Alert", "Please select one path")
			ok = False

		if len(self._panel_path.value.datasets)>1 and ok:
			QtGui.QMessageBox.information(self, "Alert", "Please select only one path")
			ok = False


		if self._apply.checked and ok:
			images = self._panel_imgs.value.images
			background = None if len(images)!=1 else images[0].image.copy()

			self._toolbox.enabled 		= False
			self._player.stop()		
			self._player.enabled 		= False
			self._outfile.enabled 		= False	
			self._apply.label 			= 'Cancel'

			areas  = self._panel_area.value.datasets
			colors = self._panel_colors.value.datasets
			images = self._panel_imgs.value.images

			for video, (begin,end), paths in self._panel_path.value.selected_data:
				if not self._apply.checked:	break

				self._progress.min = 0
				self._progress.max = (end-begin)
				self._progress.show()
					
				codec = int(video.video_capture.get(cv2.CAP_PROP_FOURCC))
				fps   = int(video.video_capture.get(cv2.CAP_PROP_FPS))

				if background is None:
					size = int(video.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
					capture = cv2.VideoCapture(video.filepath)
					capture.set(cv2.CAP_PROP_POS_FRAMES, begin)
				else:
					size = background.shape[1], background.shape[0]
					capture = None

				outputvideo = cv2.VideoWriter(self._outfile.value, codec, fps, size)

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
						area  	 = self.__get_object_area(path, areas, index)			
						color 	 = self.__get_object_color(path, colors, index)

						if position is not None and area is not None and color is not None:
							radius = int(round(math.sqrt(area/math.pi)))
							cv2.circle(frame, position, radius, color, -1)

						self._progress.value = index					
						outputvideo.write(frame)

				outputvideo.release()

			self._toolbox.enabled 		= True
			self._player.enabled 		= True
			self._outfile.enabled 		= True
			self._apply.label 			= 'Generate video'
			self._apply.checked 		= False
			self._progress.hide()

			
			




	


if __name__ == '__main__': 
	pyforms.startApp(VirtualObjectGeneratorWindow)
