(function(global) {
	if (typeof(require)!='undefined') {
		document = new (require('jsdom').JSDOM)().window.document;
	}
	let namespaces = {
		'svg': 'http://www.w3.org/2000/svg',
		/// s is a custom alias
		's': 'http://www.w3.org/2000/svg',
		'math': 'http://www.w3.org/1998/mathml',
		/// m is a custom alias
		'm': 'http://www.w3.org/1998/mathml',
	};
	function node(tag, ...args) {
		let nsParts = tag.split(/:/);
		let ns = null;
		if (nsParts.length>1) {
			ns = nsParts[0];
			tag = nsParts[1];
		}
		let parts = tag.split(/(?=[.#])/);
		tag = parts[0];
		let attrs = parts.slice(1);
		let el = ns ? document.createElementNS(namespaces[ns], tag) : document.createElement(tag);
		let attr = null;
		let arg = null;
		let i = 0;
		for (i=0; i<attrs.length; i++) {
			attr = attrs[i];
			if (attr[0] == '.')  el.classList.add(attr.slice(1));
			else if (attr[0] == '#')  el.id = attr.slice(1);
		}
		for (i=0; i<args.length; i++) {
			arg = args[i];
			handleArg(el, arg);
		}
		
		return el;
	}

	function qnode(tag, ...args) {
		let el = document.createElement(tag);

		for (i=0; i<args.length; i++) {
			arg = args[i];
			handleArg(el, arg);
		}

		return el;
	}

	function handleArg(el, arg) {
		let type = typeof arg;
		let containerEl = el;
		
		/// Blah to special casing :(
		/// This at least makes it work seamlessly with HTML
		if (el.tagName == 'TEMPLATE') {
			containerEl = el.content;
		}
		
		if (arg === null || arg === undefined) {
			/// pass
		}
		/// This is far quicker than instanceof, though more prone to error
		else if (arg && arg.nodeType && arg.nodeName) {
		//else if (arg instanceof Element || arg instanceof DocumentFragment) {
			containerEl.appendChild(arg);
		}
		else if (Array.isArray(arg)) {
			let args = arg;
			for (var arg of args) {
				handleArg(el, arg);
			}
		}
		else if (type == "string" || type == "number" || type == "boolean") {
			containerEl.appendChild(document.createTextNode(String(arg)));
		}
		else {
			for (var attr in arg) {
				var attrVal = arg[attr];
				if (attr in node.hooks)  node.hooks[attr](el, attrVal, attr);
				else if (attrVal===null || attrVal===undefined) ;
				else {
					/// Convert mixedCase to mixed-case
					attr = attr.replace(/[A-Z]/g, m => '-'+m.toLowerCase());
					el.setAttribute(attr, String(attrVal));
				}
			}
		}
	}

	/// Attributes that do custom things. Recommend prefixing with 'hook'. JS style names only.
	node.hooks = {}
	var n = node;

	/// A rather important hook
	node.hooks.on = (el, obj) => {
		for (var [eventName,func] of Object.entries(obj)) {
			el.addEventListener(eventName, func);
		}
	}

	node.hooks.dataText = (el, arg) => {
		el.appendChild(document.createTextNode(String(arg)));
	}

	/*function syncNode(target, source) {
		var nodesToSync = [target];
		
	}*/
	function toHtml(str) {
		if (str===null || str===undefined)  return "";
		str = ""+str;
		str = str
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
		return str;
	}

	/** Call using html`<div>${content}</div>` or using html('<div>'+content+'</div>') **/
	function html(strs, ...keys) {
		if (strs && strs.nodeType !== undefined)  return strs;
		let str = typeof(strs)=="string" ? strs : strs[0] + keys.map((k,i) => toHtml(k)+strs[i+1]).join('');
		var wrapper = document.createElement('div');
		var range = document.createRange();
		wrapper.innerHTML = str;
		range.selectNodeContents(wrapper);
		return range.extractContents();
	}

	/** This restores jquery like chaining --- but for any object at all! **/
	function chain(o, opts = {}) {
		function chainPromise(prom, opts = {}, prevProp = null) {
			let dummy = function(){};
			let proxy = new Proxy(dummy, {
				get(target, prop) {
					if (prop == 'then') {
						/// If I have to call back await (or some other then() call's callback),
						/// return the promise immediately
						return r => r(prom);
					}
					//onsole.log(prop);
					/** Special case function to be a function that returns a promise, rather than promise **/
					return chainPromise(prom.then(v => chain(v, opts)[prop]), opts);
				},
				apply(target, thisArg, args) {
					return chainPromise(prom.then(v => v(...args)), opts);
				},
			});
			opts.root ??= proxy;
			return proxy;
		}

		let chainSym = Symbol('chain');
		if (typeof(o)!='object' || o == null || o[chainSym])  return o;
		let handler = {get(target,prop,receiver,noCustomProps) {
			if (!noCustomProps) {
				if (prop === 'my') {
					return new Proxy(proxy, {get(_target,_prop) {
						//onsole.log(target,_prop, prop);
						return handler.get(target,_prop,receiver,true);
					}});
				}
				else if (prop === 'root') {
					return opts.root;
				}
				else if (prop === 'set') {
					/** return function to set things **/
					return (obj) => {
						Object.assign(target, obj);
						/// return the root of the chain (i.e. the original proxy)
						return proxy;
					};
				}
				else if (prop === 'unchain') {
					return _=> target;
				}
				/// More experimental:
				else if (prop === 'forEach') {
					return func => {
						target.forEach((element,index,array) => func(chain(element, opts),index,array));
						return proxy;
					}
				}
				else if (prop === 'toString') {
					return _=> target;
				}
			}
			if (!(prop in target))  return undefined;
			
			if (typeof(target[prop])=='function') {
				return (...args) => {
					//onsole.log('called',prop)
					let val = target[prop](...args);
					if (typeof(val)=='object' && val != null) {
						if (typeof(val.then)=='function') {
							//onsole.log('function call returned thenable:', target, prop);
							return chainPromise(val, opts);
						}
						else {
							return chain(val, opts);
						}
					}
					else if (val == null) {
						return proxy;
					}
					else {
						return val;
					}
				}
			}
			else if (typeof(target[prop])=='object' && target[prop] != null) {
				if (typeof(target[prop].then)=='function') {
					return chainPromise(target[prop], opts);
				}
				else {
					return chain(target[prop], opts);
				}
			}
			else {
				return target[prop];
			}
		}};
		let proxy = new Proxy(o, handler);
		proxy[chainSym] = true;
		opts.root ??= proxy;
		return proxy;
	}

	global.node = node;
	global.qnode = qnode;
	global.n = n;
	global.q = str => chain(document.querySelector(str));
	global.qa = str => chain(document.querySelectorAll(str));
	global.toHtml = toHtml;
	global.html = html;
	global.chain = chain;
})(typeof(window)!='undefined' ? window : exports);