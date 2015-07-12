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
 * @var   source   raw source code for this namespace
 * @var   structs  represents all forward declared structs of namespace
 * @var   defines  represents all #defines of the namespace
 * @var   commands represents all commands in the namespace
 * @var   types    represents all typedefs in the namespace
 * @var   empty    whether if namespace is nothing but a namespace!
 *
 * @param codename the string extracted from #ifndef GL_**
 * @see   GlCoreParser::ParseNamespaces
 */
function Namespace(codename) {
	
	this.codename = "";
	this.name     = "";
	this.vendor   = "";
	this.source   = "";
	this.commands = [];
	this.structs  = [];
	this.defines  = [];
	this.types    = [];
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

/*!
 * @class GlCoreParser
 * @brief This class uses source provided by GlCoreHeader and parses
 *        all information needed to generate the final loader.
 */
function GlCoreParser() {
	// An array holding all namespaces (members instances of Namespace)
	var _namespaces = [];
	
	/*!
	 * @fn    ParseNamespaces
	 * @brief Attempts to parse all namespaces in the format of GL_**
	 * @see   Namespace
	 */
	this.ParseNamespaces = function() {
		_namespaces = [];
		var regex  = /#\s*ifndef\s+(GL_.+)\s*$/gm;
		var source = new GlCoreHeader().GetSource();
		
		var matches = regex.exec(source);
		while (matches != null) {
			// Capture group #1 will have the codename here
			_namespaces.push(new Namespace(matches[1]));
			matches = regex.exec(source);
		}
	}
	
	/*!
	 * @fn    GetNamespaces
	 * @brief Returns the namespaces parsed from glcorearb.h
	 */	
	this.GetNamespaces = function() {
		return _namespaces;
	}
	
	/*!
	 * @fn    ExtractSources
	 * @brief Extracts raw source codes for each namespace
	 */	
	this.ExtractSources = function() {
		var _ns = this.GetNamespaces();
		var _src = new GlCoreHeader().GetSource();
		_ns.forEach(function(namespace, index) {
			var regex_str =
				'#\\s*define\\s+' + namespace.codename + '.*$' +
				'([^]*)#\\s*endif.+' + namespace.codename + '.*$';
			var regex = new RegExp(regex_str, 'gm');
			_namespaces[index].source = ((regex.exec(_src))[1]).trim();
		});
	}

	/*!
	 * @fn    CleanSources
	 * @brief Removes unnecessary code from sources
	 */	
	this.CleanSources = function() {
		var _ns = this.GetNamespaces();
		_ns.forEach(function(namespace, index) {
			var re = /#\s*ifdef.*|#\s*endif.*/g;
			_namespaces[index].source = namespace.source.replace(re,'');
			if (_namespaces[index].source.trim().length == 0)
				_namespaces[index].empty = true;
		});
	}
	
	/*!
	 * @fn    ParseTypes
	 * @brief Parses simple typedefs out of the source, Like GLboolean.
	 */
	this.ParseTypes = function() {
		var _ns = this.GetNamespaces();
		_ns.forEach(function(namespace, index) {
			var regex = // There is no pointer typedef like GLHandle ...
		    /typedef\s+([a-zA-Z0-9]+\s+[a-zA-Z0-9]*)\s+([a-zA-Z0-9]+);/gm;
			var match = regex.exec(namespace.source);
			while (match != null) {
				// [1] is type, [2] is its alias
				_namespaces[index].types.push({
					'type'  : (match[1]).trim() ,
					'alias' : (match[2]).trim()
				});
				match = regex.exec(namespace.source);
			}
		});
	}
	
	/*!
	 * @fn    ParseDefines
	 * @brief Parses defines out of the source, these will be enums.
	 */
	this.ParseDefines = function() {
		var _ns = this.GetNamespaces();
		_ns.forEach(function(namespace, index) {
			var regex = /#\s*define\s+([A-Z_]+)\s+(.*)$/gm;
			var match = regex.exec(namespace.source);
			while (match != null) {
				// [1] is name, [2] is its value
				_namespaces[index].defines.push({
					'name'  : (match[1]).trim() ,
					'value' : (match[2]).trim()
				});
				match = regex.exec(namespace.source);
			}
		});
	}
	
	/*!
	 * @fn    ParseCommands
	 * @brief Parses function pointers and their signature.
	 */
	this.ParseCommands = function() {
		var _ns = this.GetNamespaces();
		_ns.forEach(function(namespace, index) {
			var regex = /.*(PFN[A-Z0-9]+).*/gm;
			var match = regex.exec(namespace.source);
			while (match != null) {
				// [1] is ptrname
				var command = {
					'ptrname' : (match[1]).trim() ,
					'funptr'  : (match[0]).trim() ,
					'proto'   : '' ,
					'name'    : ''
				};
				
				// Let's find the prototype
				var re_str =
				   'GLAPI.*' + 
				   command.ptrname.replace(/PFN|PROC/g, '') +
				   '.*';
				var re_obj = new RegExp(re_str, 'gmi');
				command.proto = namespace.source.match(re_obj)[0];
				
				// Let's get the command name
				re_str = command.ptrname.replace(/PFN|PROC/g, '');
				re_obj = new RegExp(re_str, 'gi');
				command.name = command.proto.match(re_obj)[0];
				
				_namespaces[index].commands.push(command);
				match = regex.exec(namespace.source);
			}
		});
	}
	
	/*!
	 * @fn    ParseStructs
	 * @brief Parses struct forward decls
	 * @note  This is unnecessary and it's mostly for cl_** but here for
	 *        the sake of completeness it is included.
	 */
	this.ParseStructs = function() {
		var _ns = this.GetNamespaces();
		_ns.forEach(function(namespace, index) {
			var regex = /struct\s+([a-zA-Z0-9_]+);$/gm;
			var match = regex.exec(namespace.source);
			
			while(match != null) {
				_namespaces[index].structs.push(match[1].trim());
				match = regex.exec(namespace.source);
			}
		});
	}
	
	/*!
	 * @fn    Parse
	 * @brief Parses the string source in GlCoreHeader.
	 */		
	this.Parse = function() {
		this.ParseNamespaces();
		this.ExtractSources();
		this.CleanSources();
		this.ParseTypes();
		this.ParseDefines();
		this.ParseCommands();
		this.ParseStructs();
	}
	
	// parse the header on construction
	this.Parse();
}

/*!
 * @class GlCoreWriter
 * @brief Generates the C++ header based on what parser has parsed.
 */
function GlCoreWriter(parser) {
	if (!(parser instanceof GlCoreParser))
		throw "Invalid Parser type passed. Please pass a GlCoreParser";
	
	// Just in case...
	parser.Parse();
	
	// TODO
}

module.exports = {
	'header' : GlCoreHeader ,
	'parser' : GlCoreParser ,
	'writer' : GlCoreWriter
}
