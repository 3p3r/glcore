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

prefixHeaderString = '''#pragma once

#include <cinttypes>
#include <cstddef>

#if !defined(_WIN32) && (defined(__WIN32__) || defined(WIN32) || defined(__MINGW32__))
#	define _WIN32
#endif /* _WIN32 */
#ifndef APIENTRY
#   ifdef _WIN32
#	   define APIENTRY __stdcall
#   else
#	   define APIENTRY
#   endif
#endif /* APIENTRY */

#if defined _WIN32 || defined __CYGWIN__
#	define GLCOREDLL_IMPORT __declspec(dllimport)
#	define GLCOREDLL_EXPORT __declspec(dllexport)
#else
#	if __GNUC__ >= 4
#		define GLCOREDLL_IMPORT __attribute__ ((visibility ("default")))
#		define GLCOREDLL_EXPORT __attribute__ ((visibility ("default")))
#	else
#		define GLCOREDLL_IMPORT
#		define GLCOREDLL_EXPORT
#	endif /* __GNUC__ */
#endif /* _WIN32 */

#ifdef GLCORE_DLL // defined if GlCore is compiled as a DLL
#	ifdef GLCORE_DLL_EXPORTS // defined if we are building the GlCore DLL (instead of using it)
#		define GLCOREAPI GLCOREDLL_EXPORT APIENTRY
#	else
#		define GLCOREAPI GLCOREDLL_IMPORT APIENTRY
#	endif /* GLCORE_DLL_EXPORTS */
#else // GLCORE_DLL is not defined: this means GlCore is a static lib.
#	define GLCOREAPI APIENTRY
#endif /* GLCORE_DLL */
'''

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
				 apicall = 'GLCOREAPI ',
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
		self.groupDict = None
		self.prototypes = ''
	
	def makeGroupDictIfNotExist(self, elem):
		if self.groupDict == None:
			self.groupDict = {}
			# hack: to find all groups
			for group in elem.getparent().findall('groups/group'):
				group_name = group.get('name')
				for enum in group.findall('enum'):
					enum_name = enum.get('name')
					if enum_name not in self.groupDict:
						self.groupDict[enum_name] = []
					self.groupDict[enum_name].append(group_name)
	
	def newline(self):
		write('', file=self.outFile)
	
	def writeline(self, str):
		write(str, file=self.outFile)
	
	def beginFile(self, genOpts):
		OutputGenerator.beginFile(self, genOpts)
		self.rootNamespace = genOpts.apiname + genOpts.profile
		self.writeline(prefixHeaderString)
		self.writeline('namespace ' + self.rootNamespace)
		self.writeline('{')
		self.newline();

	def endFile(self):
		self.writeline('} //!namespace ' + self.rootNamespace)
		OutputGenerator.endFile(self)
		
	def beginFeature(self, interface, emit):
		self.makeGroupDictIfNotExist(interface)
		OutputGenerator.beginFeature(self, interface, emit)
		self.currentFeature = FeatureInfo(interface)
		self.genNamespaceBegin()
		
	def endFeature(self):
		self.genEnums()
		self.genCmds()
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
		if name in ('inttypes', 'stddef'):
			return
		typeElem = typeinfo.elem
		s = noneStr(typeElem.text)
		for elem in typeElem:
			if (elem.tag == 'apientry'):
				s += self.genOpts.apientry + noneStr(elem.tail)
			else:
				s += noneStr(elem.tail)
		if name.startswith('struct'):
			s = name + s;
		else:
			s = s.replace(' ;', ';')
			s = s.replace('  *)', ' *)')
			s = s.replace('typedef', 'using ' + name + ' =')
		self.writeline(s)

	def genEnum(self, enuminfo, name):
		OutputGenerator.genEnum(self, enuminfo, name)
		t = enuminfo.elem.get('type')
		if t == '' or t == None:
			t = 'i' #hack: to force type to be int for non suffixed ones
		if t == 'i' or t == 'u' or t == 'ull':
			self.enumTypes[t] += name.ljust(47) + ' = ' + enuminfo.elem.get('value') + ( t if t != 'i' else '' )
			self.enumTypes[t] += ","
			if name in self.groupDict:
				self.enumTypes[t] += ' /* '
				for group in self.groupDict[name]:
					self.enumTypes[t] += (group + ' ')
				self.enumTypes[t] += '*/'
			self.enumTypes[t] += "\n"
		else:
			raise Exception('Unknown enum type found: ' + t)
	
	def genEnums(self):
		for enumType in self.enumTypes:
			enumBody = self.enumTypes[enumType]
			if enumBody != '':
				enumBody += '}; //!enum'
				cppType = ''
				if enumType == 'u':
					cppType = ' : unsigned'
				elif enumType == 'ull':
					cppType = ' : unsigned long long'
				self.writeline('enum' + cppType + ' {')
				self.writeline(enumBody)
				self.newline()
				self.enumTypes[enumType] = ''

	def genCmd(self, cmdinfo, name):
		OutputGenerator.genCmd(self, cmdinfo, name)
		self.prototypes += (self.makePrototype(cmdinfo.elem))
	
	def genCmds(self):
		if self.prototypes != '':
			self.writeline(self.prototypes)
		self.prototypes = ''
	
	def makePrototype(self, cmd):
		proto = cmd.find('proto')
		params = cmd.findall('param')
		pdecl = self.genOpts.apicall
		pdecl += noneStr(proto.text)
		for elem in proto:
			text = noneStr(elem.text)
			tail = noneStr(elem.tail)
			pdecl += text + tail
		n = len(params)
		paramdecl = ' ('
		if n > 0:
			for i in range(0,n):
				paramdecl += ''.join([t for t in params[i].itertext()])
				if (i < n - 1):
					paramdecl += ', '
		else:
			paramdecl += 'void'
		paramdecl += ");\n";
		return pdecl + paramdecl

# Load & parse registry
reg = Registry()
reg.loadElementTree(etree.parse('gl.xml'))
reg.setGenerator(CppOutputGenerator())
reg.apiGen(CppGeneratorOptions())

print 'Done.'
