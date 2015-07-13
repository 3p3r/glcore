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
                 filename = 'glcorearb.h',
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
        
        self.apicall         = apicall
        self.apientry        = apientry
        self.apientryp       = apientryp

class CppOutputGenerator(OutputGenerator):
    """Generate specified API interfaces as a C++ header"""
    def __init__(self,
                 errFile = None, #sys.stderr,
                 warnFile = None, #sys.stderr,
                 diagFile = None): #sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
    
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

    def endFile(self):
        OutputGenerator.endFile(self)
        
    def beginFeature(self, interface, emit):
        OutputGenerator.beginFeature(self, interface, emit)
        
    def endFeature(self):
        OutputGenerator.endFeature(self)

    def genType(self, typeinfo, name):
        OutputGenerator.genType(self, typeinfo, name)

    def genEnum(self, enuminfo, name):
        OutputGenerator.genEnum(self, enuminfo, name)

    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)

# Load & parse registry
reg = Registry()
reg.loadElementTree(etree.parse('gl.xml'))
reg.setGenerator(CppOutputGenerator())
reg.apiGen(CppGeneratorOptions())

print 'Done.'
