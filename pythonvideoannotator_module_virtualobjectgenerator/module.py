import cv2
from pysettings import conf
from pythonvideoannotator_module_virtualobjectgenerator.virtualobjectgenerator_window import VirtualObjectGeneratorWindow


class Module(object):

	def __init__(self):
		"""
		This implements the Path edition functionality
		"""
		super(Module, self).__init__()


		self.virtualobjectgenerator_window = VirtualObjectGeneratorWindow(self)


		self.mainmenu[1]['Modules'].append(
			{'Virtual object generator': self.virtualobjectgenerator_window.show, 'icon':conf.ANNOTATOR_ICON_PATH },			
		)



	
	######################################################################################
	#### IO FUNCTIONS ####################################################################
	######################################################################################

	
	def save(self, data, project_path=None):
		data = super(Module, self).save(data, project_path)
		data['virtualobjectgenerator-settings'] = self.virtualobjectgenerator_window.save_form({})
		return data

	def load(self, data, project_path=None):
		super(Module, self).load(data, project_path)
		if 'virtualobjectgenerator-settings' in data: self.virtualobjectgenerator_window.load_form(data['virtualobjectgenerator-settings'])
		