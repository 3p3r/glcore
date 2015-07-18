import os, urllib

REG_PY_URL = 'https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/reg.py';
GL_XML_URL = 'https://cvs.khronos.org/svn/repos/ogl/trunk/doc/registry/public/api/gl.xml';

if not os.path.isfile('reg.py'):
	print 'reg.py not found. Downloading...'
	urllib.urlretrieve(REG_PY_URL, 'reg.py')
else:
	print 'Found reg.py. Reusing it...'

if not os.path.isfile('gl.xml'):
	print 'gl.xml not found. Downloading...'
	urllib.urlretrieve(GL_XML_URL, 'gl.xml')
else:
	print 'Found gl.xml. Reusing it...'

if not os.path.isfile('reg.py') or not os.path.isfile('reg.py'):
	raise Exception('Either reg.py or gl.xml does not exist.')

print 'Began API generation...'
from reg import *

class CppGeneratorOptions(GeneratorOptions):
	"""Represents options during C++ header generation"""
	def __init__(self,
				 filename = 'glcore.h',
				 apiname = 'gl',
				 profile = 'core',
				 versions = '.*',
				 emitversions = '.*',
				 defaultExtensions = 'glcore',
				 addExtensions = None,
				 removeExtensions = None,
				 sortProcedure = regSortFeatures,
				 apicall = 'GLAPI ',
				 apientry = 'APIENTRY ',
				 apientryp = 'APIENTRYP '):
		GeneratorOptions.__init__(self, filename, apiname, profile,
			versions, emitversions, defaultExtensions,
			addExtensions, removeExtensions, sortProcedure)
		
		self.apicall		 = apicall
		self.apientry		= apientry
		self.apientryp	   = apientryp

from pprint import pprint

class CppOutputGenerator(OutputGenerator):
	"""Generate specified API interfaces as a C++ header"""
	def __init__(self,
				 errFile = None, #sys.stderr,
				 warnFile = None, #sys.stderr,
				 diagFile = None): #sys.stdout):
		OutputGenerator.__init__(self, errFile, warnFile, diagFile)
		#internal bookkeeping
		self.currentFeature = None
		self.currentNamespace = ''
		self.rootNamespace = ''
		self.dependentVersion = None #highest version available
		self.enumTypes = { 'i' : '', 'u': '', 'ull' : '' }
	
	def newline(self):
		write('', file=self.outFile)
	
	def writeline(self, str):
		write(str, file=self.outFile)
	
	def beginFile(self, genOpts):
		OutputGenerator.beginFile(self, genOpts)
		self.rootNamespace = genOpts.apiname + genOpts.profile
		self.writeline('namespace ' + self.rootNamespace)
		self.writeline('{')
		self.newline();

	def endFile(self):
		self.writeline('} //!namespace ' + self.rootNamespace)
		OutputGenerator.endFile(self)
		
	def beginFeature(self, interface, emit):
		OutputGenerator.beginFeature(self, interface, emit)
		self.currentFeature = FeatureInfo(interface)
		self.genNamespaceBegin()
		
	def endFeature(self):
		self.genEnums()
		self.genNamespaceEnd()
		self.currentFeature = None
		OutputGenerator.endFeature(self)
	
	def isFeatureApi(self):
		return self.currentFeature.category == 'VERSION'
	
	def genNamespaceBegin(self):
		if self.isFeatureApi():
			self.writeline('namespace api {')
			self.genApiNamespaceBegin()
			self.genDependentNamespace()
		else:
			self.writeline('namespace ' + self.currentFeature.category.lower() + ' {')
			self.genExtNamespaceBegin()
			self.genDependentNamespace()
	
	def genDependentNamespace(self):
		if self.dependentVersion != None:
			self.writeline('using namespace api::v' + self.dependentVersion + ';')
			self.newline()
	
	def genNamespaceEnd(self):
		if self.isFeatureApi():
			self.genApiNamespaceEnd()
			self.writeline('} //!namespace api')
			self.dependentVersion = self.currentNamespace
		else:
			self.genExtNamespaceEnd()
			self.writeline('} //!namespace ' + self.currentFeature.category.lower())
		self.newline()
	
	def genApiNamespaceBegin(self):
		self.currentNamespace = self.currentFeature.number.replace('.', '')
		self.writeline('namespace v' + self.currentNamespace + ' {')
		self.newline()
	
	def genApiNamespaceEnd(self):
		self.writeline('} //!namespace v' + self.currentNamespace)
	
	def genExtNamespaceBegin(self):
		self.currentNamespace = self.currentFeature.name.replace('GL_' + self.currentFeature.category + '_', '').lower()
		self.writeline('namespace ' + self.currentNamespace + ' {')
		self.newline()
	
	def genExtNamespaceEnd(self):
		self.writeline('} //!namespace ' + self.currentNamespace)

	def genType(self, typeinfo, name):
		OutputGenerator.genType(self, typeinfo, name)

	def genEnum(self, enuminfo, name):
		OutputGenerator.genEnum(self, enuminfo, name)
		t = enuminfo.elem.get('type')
		if t == '' or t == None:
			t = 'i' #hack: to force type to be int for non suffixed ones
		if t == 'i' or t == 'u' or t == 'ull':
			self.enumTypes[t] += name.ljust(47) + ' = ' + enuminfo.elem.get('value') + ( t if t != 'i' else '' )
			self.enumTypes[t] += ",\n"
		else:
			raise Exception('Unknown enum type found: ' + t)
	
	def genEnums(self):
		for enumType in self.enumTypes:
			enumBody = self.enumTypes[enumType]
			if enumBody != '':
				enumBody += '}' #hack alert!
				cppType = ''
				if enumType == 'u':
					cppType = ' : unsigned'
				elif enumType == 'ull':
					cppType = ' : unsigned long long'
				self.writeline('enum' + cppType + ' {')
				self.writeline(enumBody.replace(',\n}', '\n}; //!enum'))
				self.newline()
				self.enumTypes[enumType] = ''

	def genCmd(self, cmdinfo, name):
		OutputGenerator.genCmd(self, cmdinfo, name)

# Load & parse registry
reg = Registry()
reg.loadElementTree(etree.parse('gl.xml'))
reg.setGenerator(CppOutputGenerator())
reg.apiGen(CppGeneratorOptions())

print 'Done.'
