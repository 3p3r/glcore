/*!
 * @class  GlCoreHeader
 * @brief  A singleton class holding information about glcorearb.h
 * @credit http://stackoverflow.com/a/6733919/388751
 * @usage  new GlCoreHeader().GetSource() //returns the source string
 */
function GlCoreHeader() {
	if ( arguments.callee._singletonInstance )
		return arguments.callee._singletonInstance;
	arguments.callee._singletonInstance = this;

	Source = (function() {
		return require('fs').readFileSync('glcorearb.h', 'utf8');
	})();
	
	/*!
	 * \fn     GetSource
	 * \brief  returns the glcorearb.h source code as string
	 * \return string
	 */
	this.GetSource = function() {
		return Source;
	}
}

/*!
 * @class Namespace
 * @brief A class containing information about an OpenGL namespace.
 * @note  Based on what is available in current glcorearb.h, everything
 *        is wrapped inside #ifndef's. Therefore this script assumes a
 *        namespace starts with a #ifndef GL_**.
 *
 * @var   codename the original name of the namespace (including GL_)
 * @var   name     the actual name of the namespace
 * @var   vendor   the vendor name of the namespace (ARB for example)
 * @var   funptrs  represents all function pointers inside the namespace
 * @var   structs  represents all forward declared structs of namespace
 * @var   defines  represents all #defines of the namespace
 * @var   protos   represents all function prototypes in the namespace
 * @var   empty    whether if namespace is nothing but a namespace!
 *
 * @param codename the string extracted from #ifndef GL_**
 * @see   GlCoreParser::ParseNamespaces
 */
function Namespace(codename) {
	
	this.codename = "";
	this.name     = "";
	this.vendor   = "";
	this.funptrs  = [];
	this.structs  = [];
	this.defines  = [];
	this.protos   = [];
	this.empty    = false;
	
	// Do we have a valid codename ?
	if (codename.indexOf("GL_") < 0) {
		throw "Invalid codename. It should start with GL_ prefix";
	}
	// store the codename
	this.codename = codename;
	codename = codename.toLowerCase()
	
	if (codename.indexOf("version") > 0) {
		// This is not a vendor / extension namespace
		var regex = /gl_version_([0-9])_([0-9])/g;
		var match = regex.exec(codename);
		var version_major = match[1];
		var version_minor = match[2];
		this.name = "v" + version_major + version_minor;
	} else {
		// belongs to an extension and has a vendor
		var regex = /gl_([a-z0-9]+)_(.+)/g;
		var match = regex.exec(codename);
		var vendor = match[1];
		var extname = match[2];
		this.name = extname;
		this.vendor = vendor;
	}
};

function GlCoreParser() {
	// An array holding all namespaces
	_namespaces = [];
	
	this.CodenameToName
	
	this.ParseNamespaces = function() {
		var regex  = /#\s*ifndef\s+(GL_.+)\s*$/gm;
		var source = new GlCoreHeader().GetSource();
		
		var matches = regex.exec(source);
		while (matches != null) {
			// Capture group #1 will have the codename here
			_namespaces.push(new Namespace(matches[1]));
			matches = regex.exec(source);
		}
	}
	
	this.GetNamespaces = function() {
		return _namespaces;
	}
}

var test = new GlCoreParser();
test.ParseNamespaces();
console.log(test.GetNamespaces());