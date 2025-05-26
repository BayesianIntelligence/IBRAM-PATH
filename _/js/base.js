/// From https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Function/bind
if (!Function.prototype.bind) {
	Function.prototype.bind = function (oThis) {
		if (typeof this !== "function") {
		  // closest thing possible to the ECMAScript 5 internal IsCallable function
		  throw new TypeError("Function.prototype.bind - what is trying to be bound is not callable");
		}

		var aArgs = Array.prototype.slice.call(arguments, 1),
		    fToBind = this,
		    fNOP = function () {},
		    fBound = function () {
		      return fToBind.apply(this instanceof fNOP
					     ? this
					     : oThis || window,
					   aArgs.concat(Array.prototype.slice.call(arguments)));
		    };

		fNOP.prototype = this.prototype;
		fBound.prototype = new fNOP();

		return fBound;
	};
}

if (!Array.prototype.findIndex) {
  Object.defineProperty(Array.prototype, 'findIndex', {value: function(predicate) {
	if (this === null) {
	  throw new TypeError('Array.prototype.findIndex called on null or undefined');
	}
	if (typeof predicate !== 'function') {
	  throw new TypeError('predicate must be a function');
	}
	var list = Object(this);
	var length = list.length >>> 0;
	var thisArg = arguments[1];
	var value;

	for (var i = 0; i < length; i++) {
	  value = list[i];
	  if (predicate.call(thisArg, value, i, list)) {
		return i;
	  }
	}
	return -1;
  }});
}

function unionArrays(x, y) {
  var obj = {};
  for (var i = x.length-1; i >= 0; -- i)
     obj[x[i]] = x[i];
  for (var i = y.length-1; i >= 0; -- i)
     obj[y[i]] = y[i];
  var res = []
  for (var k in obj) {
    if (obj.hasOwnProperty(k))  // <-- optional
      res.push(obj[k]);
  }
  return res;
}

function genPass(length) {
	var pwd;
	pwd = "";
	for (i=0;i<length;i++) {
		pwd += String.fromCharCode(Math.floor((Math.random()*25+65)));
	}
	return pwd.toLowerCase();
}

function nullValue(val, valIfNull) {
	if (arguments.length==1) {
		valIfNull = null;
	}
	if (val===null || val===undefined) {
		return valIfNull;
	}
	return val;
}

/// I'm not sure if this guarantees a nicely formatted string.
function sigFig(num, digits) {
	if (num==0)  return 0;
	var sign = Math.sign(num);
	num = Math.abs(num);
	/// Get a multiplier based on the log position of most sig digit (add 1 to avoid 100...0 not being rounded up)
	var mul = Math.pow(10,Math.floor(Math.log10(num)));
	var sigPow = Math.pow(10,digits-1);
	/// XXX: I need to work this out properly at some point
	var v = Math.round((num/mul)*sigPow);
	if ((mul/sigPow) < 1) {
		var d = Math.round(1/(mul/sigPow));
		v = v/d;
	}
	else {
		var d = Math.round(mul/sigPow);
		v = v*d;
	}

	return sign*v;
}

function getQs(searchStr) {
	searchStr = searchStr || window.location.search;
	var params = {};
	if (searchStr) {
		var argSpecs = searchStr.substring(1).split('&');
		for (var i in argSpecs) {
			var argInfo = argSpecs[i].split('=');
			params[unescape(argInfo[0])] = unescape(argInfo[1].replace(/\+/g, ' '));
		}
	}
	return params;
}

function parseQs(qs, returnArgOrder) {
	var params = {};
	var argOrder = [];
	if (qs) {
		var argSpecs = qs.split('&');
		for (var i=0; i<argSpecs.length; i++) {
			var argInfo = argSpecs[i].split('=');
			params[unescape(argInfo[0])] = unescape(argInfo[1]);
			if (returnArgOrder)  argOrder.push(unescape(argInfo[0]));
		}
	}
	if (returnArgOrder)  return {args: params, argOrder: argOrder};
	return params;
}

function changeQsUrl(url, nameValues) {
    url = url.replace(/^&|&$/g, "");
    found = url.match(/^([^?]*\??)(.*)/);
    if (found) {
    	if (found[1].charAt(found[1].length-1)!='?') {
    		found[1] += '?';
    	}
    	return found[1]+changeQs(found[2], nameValues);
    }
    return "";
}

function changeQs(qs, nameValues) {
	var qs = "&"+qs;
	for (var name in nameValues) {
		var re = new RegExp("&"+name+"=[^&]*", "gi");
		qs = qs.replace(re, "");
		qs = qs.replace(/^&/, "");
		if (nameValues[name]!==null) {
			if (qs!="") { qs += "&"; }
			qs += name + "=" + escape(nameValues[name]);
		}
	}
	qs = qs.replace(/^&/, "");
	return qs;
}

function changeBodyToSlice(url) {
	var qs = parseQs(url.replace(/^([^?]*\??)(.*)$/, '$2'));
	if (qs.body) {
		url = changeQsUrl(url, {body: null, slice: qs.body});
	}
	return url;
}

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

function collectForm(form) {
	var args = {};
	for (var i=0; i<form.elements.length; i++) {
		/*if (form.elements[i].length && form.elements[i][0].type=="radio") {
			//onsole.debug(form.elements[i][j].value, form.elements[i][j].checked);
			for (var j=0; j<form.elements[i][j].length; j++) {
				if (form.elements[i][j].checked) {
					//onsole.debug(form.elements[i][j].value, form.elements[i][j].checked);
					args[form.elements[i][j].name] = form.elements[i][j].value;
				}
			}
		}
		else {*/
		if (form.elements[i].type == "radio") {
			if (form.elements[i].checked) {
				/// Need to use jquery to get value, because placeholder plugin acts funny otherwise
				args[form.elements[i].name] = $(form.elements[i]).val();
			}
		}
		else if (form.elements[i].type == "checkbox") {
			if (form.elements[i].checked) {
				args[form.elements[i].name] = $(form.elements[i]).val();
			}
		}
		else {
			args[form.elements[i].name]
				= $(form.elements[i]).val();
		}
		//}
	}
	return args;
}

function getLabelText($element) {
	$element = $($element);

	var $label = $("label[for='"+$element.attr('id')+"']");

	if ($label.length == 0) {
		$label = $element.closest('label')
	}

	if ($label.length == 0) {
		$label = $element.prev('label');
	}

	if ($label.length == 0) {
		$label = $element.next('label');
	}

	return $label.length ? $label.eq(0).text() : null;
}

/// This is for validateForm. Functions work in both js and python (and php, for that matter)
function iif(test, branchA, branchB) {
	return test ? branchA : branchB;
}

/// Use _if instead of iif
function _if(test, branchA, branchB) {
	return test ? branchA : branchB;
}

function _and() {
	var res = true;
	for (var i=0; i<arguments.length; i++) {
		res = res && arguments[i];
	}
	return res;
}

function _or() {
	var res = false;
	for (var i=0; i<arguments.length; i++) {
		res = res || arguments[i];
	}
	return res;
}

function validateForm(args, validSpec, ifFailed, formSelector) {
	var form = null;

	$(".validError").removeClass("validError");
	if (args.tagName == "FORM") {
		form = args;
		args = collectForm(args);
	}
	else if (formSelector) {
		form = $(formSelector)[0];
	}
	validSpec = typeof(args)=="string" ? JSON.parse(validSpec) : validSpec;

	var numAsync = 0;
	var errors = [];
	var asyncDone = function() {
		numAsync--;
		if (numAsync == 0) {
			if (handleErrors()) {
				/// Force submit, without revalidation
				$(form).off('submit.validation');
				$(form).submit();
			}
		}
	};

	for (var field in validSpec) {
		var fieldSpec = validSpec[field];
		/// FIX: Maybe default = null also should mean that it's missing
		if (typeof(fieldSpec["default"])!="undefined" && (typeof(args[field])=="undefined" || args[field]===null || args[field]==="")) {
			args[field] = fieldSpec["default"];
		}
	}

	for (var field in validSpec) {
		var fieldSpec = validSpec[field];
		var missing = false;
		/// Get specified label first, or html label, or just field name
		var fieldLabel = fieldSpec.label || getLabelText($("[name="+field+"]")) || field;
		/// Strip off colons, which are common
		fieldLabel = fieldLabel.replace(/\s*:\s*$/, '');

		if (fieldSpec.required) {
			if (typeof(args[field])=="undefined" || args[field]===null || args[field]==="") {
				errors.push({field: field,
					error: "missing",
					description: "[["+fieldLabel+"]] is missing"
				});
				missing = true;
			}
		}
		//Add a test for json validity
		if (!missing && fieldSpec.regexp) {
			//onsole.log("REGEXP", field, args[field], fieldSpec.regexp, new RegExp(fieldSpec.regexp).test(args[field]));
			var testVal = args[field];
			if (typeof(testVal)=="undefined" || testVal===null) {
				testVal = "";
			}
			var testResult = false;
			if (fieldSpec.fullMatch) {
				testVal = new String(testVal);
				var matched = testVal.match(new RegExp(fieldSpec.regexp));
				console.log("fullMatch:", testVal, fieldSpec.regexp, matched, testVal.length, matched[0].length);
				if (matched && matched[0].length == testVal.length) {
					testResult = true;
				}
			}
			else {
				testResult = new RegExp(fieldSpec.regexp).test(testVal);
			}
			if (!testResult) {
				var explanation = "[["+fieldLabel+"]] is not in the required format"
						+ (fieldSpec.regexpExplain ? " ("+fieldSpec.regexpExplain+")" : "");
				if (fieldSpec.explain) {
					explanation = fieldSpec.explain.replace(new RegExp("\\[\\["+field+"\\]\\]", "g"), "[["+fieldLabel+"]]");
				}
				errors.push({field: field,
					error: "failedRegexp",
					description: explanation
				});
			}
		}
		if (!missing && fieldSpec.percent) {
			var testVal = args[field];

			if (typeof(testVal)=="undefined" || testVal===null) {
				testVal = "";
			}

			testVal = Number(testVal.replace(/%\s*$/, ''));

			if (isNaN(testVal)) {
				var explanation = "[["+fieldLabel+"]] is not a percentage";
				errors.push({field: field,
					error: "failedPercent",
					description: explanation
				});
			}
		}
		if (!missing && fieldSpec.expr) {
			/*var testExpr = fieldSpec.expr.replace(/".*"|\w+/g, function(m) {
				return 'args["'+m+'"]';
			});*/
			var argNames = "";
			var sep = "";
			var argVals = [];
			for (var k in args) {
				if (!k)  continue;
				argNames += sep + k; //Removed dollar sign (which I used for PHP)
				sep = ", ";
				argVals.push(args[k]);
			}
			console.log(argNames, args, fieldSpec.expr);
			var testFunc = new Function(argNames, 'return '+fieldSpec.expr);
			if (!testFunc.apply(null, argVals)) {
				errors.push({field: field,
					error: "failedExpr",
					description: fieldSpec.exprExplain
				});
			}
		}
		if (!missing && fieldSpec.sliceCheck) {
			var sliceName = fieldSpec.sliceCheck;

			numAsync++;
			$.get("?slice="+sliceName, args, function(data) {
				console.log(data);
				if (data!=="0") {
					errors.push({field: field,
						error: "failedServerCheck",
						description: data});
				}
				asyncDone();
			});
		}
	}

	function handleErrors() {
		console.log(errors, errors.length);
		if (errors.length>0) {
			if (ifFailed) {
				return ifFailed(errors);
			}
			else {
				if (window._htmlAlert) {
					var str = "<p>The form had the following issues:<ul>";
					for (var i in errors) {
						str += "<li>"+errors[i].description.replace(/\[\[(.*?)\]\]/g, '<strong>$1</strong>');
						$("input[name="+errors[i].field+"]").addClass("validError");
					}
					str += "</ul>";
					window._htmlAlert(str, function() {
						$("input[name="+errors[0].field+"]").focus();
					});
					return false;
				}
				else {
					var str = "The form had the following issues:\n\n";
					for (var i in errors) {
						str += "\t- "+errors[i].description.replace(/\[\[(.*?)\]\]/g, "'$1'")+"\n";
						$("input[name="+errors[i].field+"]").addClass("validError");
					}
					alert(str);
					$("input[name="+errors[0].field+"]").focus();
					return false;
				}
			}
		}
		return true;
	}

	/// If not async, finish up the checking now
	if (!numAsync)  return handleErrors();

	/// Otherwise, return false now, and wait till everything done (checked by asyncDone)
	return false;
}

function setFormValidation(formSelector, validSpec, ifFailed) {
	$(formSelector).on("submit.validation", function(event) {
		var isValid = validateForm(this, validSpec, ifFailed);
		if (!isValid) {
			/// Need to prevent _anything_ else from running
			/// Make sure setFormValidation is done first
			event.stopImmediatePropagation();
			return false;
		}
	});
	window._formValidationSpec = validSpec;
	window._testValidation = function() {
		return validateForm($(formSelector)[0], validSpec, ifFailed);
	}
}

/* Using 3rd party jQuery plugin now
$.fn.bindFirst = function(name, fn) {
    // bind as you normally would
    // don't want to miss out on any jQuery magic
    this.bind(name, fn);

    // Thanks to a comment by @Martin, adding support for
    // namespaced events too.
    var handlers = this.data('events')[name.split('.')[0]];
    // take out the handler we just inserted from the end
    var handler = handlers.pop();
    // move it at the beginning
    handlers.splice(0, 0, handler);
};*/

var editTableHandlers = {
	"default": {
		edit: function($td) {
			/// Lock the (min) width and height so that the page
			/// doesn't jump around when editing. Can still
			/// jump around if control stretches the width/height
			$td
				.width($td.width())
				.height($td.height());
			$td.html(
				$("<input>").val(this.get($td))
			).find("input").select();
			var $i = $td.find("input");
			/// Use scrollIntoView plugin if present (which is much better than default browser behaviour)
			if ($i.scrollintoview)  $i.scrollintoview();
			else $i[0].scrollIntoView();
		},
		view: function($td) {
			/// Return width/height to normal
			$td
				.width("")
				.height("");
			$td.text(this.get($td));
		},
		get: function($td) {
			return $td.find("input").length ? $td.find("input").val() : $td.text();
		},
		set: function($td, val) {
			$td.find("input").length ? $td.find("input").val(val) : $td.text(val);
			return $td;
		}
	},
	textarea: {
		edit: function($td) {
			/// Lock the (min) width and height so that the page
			/// doesn't jump around when editing. Can still
			/// jump around if control stretches the width/height
			$td
				.width($td.width())
				.height($td.height());
			$td.html(
				$("<textarea>").val(this.get($td))
			).find("textarea").select();
		},
		view: function($td) {
			/// Return width/height to normal
			$td
				.width("")
				.height("");
			$td.html($("<div>").text(this.get($td)));
		},
		get: function($td) {
			return $td.find("textarea").length ? $td.find("textarea").val() : $td.text();
		},
		set: function($td, val) {
			$td.find("textarea").length ? $td.find("textarea").val(val) : $td.text(val);
			return $td;
		}
	},
	select: {
		init: function($th) {
			var col = getColumnInfo($th);
			var $sel = $("._te_"+col.name);
			getManager($th).getDataRows().each(function() {
				var $td = $(this.cells[col.index]);
				if ($td[0].tagName == "TD") {
					var val = $td.data("val")===undefined ? $td.text() : $td.data("val");
					$td.text( $sel.find("option[value='"+val+"']").text() );
					$td.data("val", val);
				}
			});
		},
		edit: function($td) {
			/// Lock the (min) width and height so that the page
			/// doesn't jump around when editing. Can still
			/// jump around if control stretches the width/height
			$td
				.width($td.width())
				.height($td.height());
			$td.empty().append(
				$("._te_"+getColumnInfo($td).name)
			).find("select").show().select().val($td.data("val"));
		},
		view: function($td) {
			/// Return width/height to normal
			$td
				.width("")
				.height("");
			var $opt = $td.find("select :selected");
			var optVal = $opt.val();
			var optText = $opt.text();
			$td.closest("table").append($td.find("select").hide());
			$td.data("val", optVal);
			$td.text(optText);
		},
		get: function($td) {
			var val = $td.find("select :selected").length
				? $td.find("select :selected").val() : $td.data("val");
			return val;
		},
		set: function($td, val) {
			//onsole.debug($td, val);
			if ($td.find("select :selected").length) {
				/// Set both the select and the td val
				$td.find("select :selected").val(val);
				$td.data("val", val);
			}
			else {
				$td.data("val", val);
				this._updateText($td);
			}
			return $td;
		},
		_updateText: function($td) {
			/* This is a hack! */
			var col = getColumnInfo($td) || this._columnInfo;
			var $sel = $("._te_"+col.name);
			$td.text( $sel.find("option[value='"+$td.data("val")+"']").text() );
		}
	},
	rowselect: {
		create: function(col, $newTr) {
			return $("<td class=field-"+col.name+">").append(
				$("<input class=rowselect type=checkbox name="+col.name+"[] value="+$newTr.data("pk")+">")
			);
		}
	},
	checkbox: {
		create: function(col, $newTr) {
			return $("<td class=field-"+col.name+">").append(
				$("<input type=checkbox>")
			);
		},
		edit: function($td) {
			return false;
		},
		view: function($td) {
			return false;
		},
		get: function($td) {
			if ($td.find("input")[0]) {
				return Boolean($td.find("input")[0].checked);
			}
			return false;
		},
		set: function($td, val) {
			if (val) {
				$td.find("input")[0].checked = val;
			}
		}
	},
	javascriptSetup: {
		// A helper function, that runs 'func' on every active td that sits
		// under th upon initialisation
		initWith: function($th, func) {
			var colInfo = getColumnInfo($th);
			$th.closest("table").find("tr:has(td)").each(function() {
				var $td = $(this.cells[colInfo.index]);
				func($td);
			});
		},
		init: function($th) {
			var f = new Function("", "return "+$th.data("jsHandler"));
			var obj = f();
			obj.initWith = this.initWith;
			if (obj.init)  obj.init($th);
			return obj;
		}
	}
};

/** Get the header row (which has all the meta info for the table **/
function getHeaderRow(el) {
	return $(el.$table || el).closest("table.editable").find("th").eq(0).closest("tr");
}

function getColumnInfo(el) {
	el = el.jquery ? el[0] : el; // data sometimes gets saved funny if applied to jquery obj
	if (!el) return null;

	// Make sure we use the cell, not anything inside it
	if (el.tagName!="TD" && el.tagName!="TH") {
		el = $(el).closest("td, th")[0];
	}

	// Might be cached to cell
	var columnInfo = $.data(el, "columnInfo");
	if (columnInfo)  return columnInfo;

	// Find th
	var $th = getHeaderRow(el).find("th:nth("+$(el).index()+")");
	if ($th.length==0) return null;

	// Might be cached to th header
	columnInfo = $.data($th[0], "columnInfo");
	if (columnInfo) {
		// Cache to cell
		$.data(el, "columnInfo", columnInfo);
		return columnInfo;
	}

	// Cache to th header and cell
	columnInfo = {
		$th: $th,
		name: $th.data("field") || $th.text().replace(/\W+/g, '_'),
		"default": $th.data("default"),
		handler: editTableHandlers[$th.data("handler") || "default"], //handler is sort of like type
		readonly: $th.data("readonly"),
		index: $th.index()
	};
	$.data(el, "columnInfo", columnInfo);
	$.data($th[0], "columnInfo", columnInfo);

	return columnInfo;
}

/*function getTh($td) {
	if ($td.data("th")) return $td.data("th");
	$td.data("th", $td.closest("table.editable").find("th").eq(0).closest("tr").find("th:nth("+$td.index()+")"));
	return $td.data("th");
}*/

$.fn.applyFunction = function(func) {
	func.apply(this[0], [$(this)].concat(Array.prototype.slice.call(arguments, 1)));
	return $(this);
}

function getManager(el) {
	return $(el).closest(".widget").data("manager");
}

var getWidget = getManager; /// 'getManager' preferred name for the function

// Editable tables
function setupEditableTables() {
	var $editTables = $("table.editable");

	$editTables.each(function() {
		var $table = $(this);
		var $widget = $table.closest(".widget");
		if ($widget.length==0) {
			$widget = $("<div class=widget/>");
			$table.wrap($widget);
			$widget = $table.closest(".widget");
		}
		/// To be more general 'editor' should be 'manager'
		$widget.data("manager", {
			$table: $table,
			$widget: $widget,
			deleted: {},
			changed: {},
			inserted: {},
			lastNewPk: -1,

			saveDone: function(newPkMap) {
				this.deleted = {};
				this.changed = {};
				this.inserted = {};
				for (var oldPk in newPkMap) {
					var newPk = newPkMap[oldPk];
					this.getRow(oldPk).attr("data-pk", newPk).data("pk", newPk);
				}
			},

			hasChanges: function() {
				var hasChanges = false;
				for (var i in this.deleted) { hasChanges = true; break; }
				for (var i in this.changed) { hasChanges = true; break; }
				for (var i in this.inserted) { hasChanges = true; break; }
				return hasChanges;
			},

			getRow: function(ref) {
				if (!ref || (typeof(ref)=="object" && $(ref).length==0)) {
					return $();
				}
				if (ref && typeof(ref)=="object") {
					if ($(ref)[0].tagName == "TR") {
						return $(ref);
					}
					else if ($(ref)[0].tagName) {
						var $m = $();
						$(ref).each(function() {
							$m = $m.add($(this).parentsUntil($table, "tr").last());
						});
						return $m;
					}
					else if (ref.pk) {
						return this.$table.find("tr[data-pk="+ref.pk+"]");
					}
				}
				// By default assumes it's a row id/primary key
				else {
					return this.$table.find("tr[data-pk="+ref+"]");
				}
			},

			deleteRow: function(ref) {
				tr = this.getRow(ref);
				var editor = this;
				$(tr).each(function() {
					editor.deleted[$(this).data("pk")] = true;
					$(this).remove();
				});
			},

			changeRow: function(ref) {
				tr = this.getRow(ref);
				var editor = this;
				$(tr).each(function() {
					editor.changed[$(this).data("pk")] = true;
				});
			},

			insertRow: function(beforeRef, initialValues, opts) {
				if (!opts)  opts = {};
				this.$table.find(".noItemsMsg").remove();
				this.lastNewPk++;
				var $newTr = $("<tr>").attr("data-pk", "_new_"+this.lastNewPk);
				this.$table.find("tr:first th").each(function() {
					var col = getColumnInfo(this);
					/* FIX: This is a hack! */
					col.handler._columnInfo = col;
					if (col.handler.create) {
						var $td = col.handler.create(col, $newTr);
						$newTr.append($td);
						if (col.handler.set) {
							$td.applyFunction(col.handler.set.bind(col.handler), col["default"]);
						}
					}
					else {
						$newTr.append(
							$("<td class=field-"+col.name+">").applyFunction(col.handler.set.bind(col.handler), col["default"])
						);
					}
				});
				var hiddenDefaults = this.$table.find("th").eq(0).closest("tr").data("hidden-defaults");
				$newTr.attr("data-hidden", JSON.stringify(hiddenDefaults)); //copy
				if (!beforeRef || $(beforeRef).length==0) {
					this.$table.find("tr:last").after($newTr);
				}
				else {
					this.getRow(beforeRef).before($newTr);
				}
				for (var key in initialValues) {
					var val = initialValues[key];
					this.setValue($newTr, key, val);
				}
				this.inserted[$newTr.data("pk")] = true;
				this.scrollToRow($newTr);
				if (opts.focus) {
					if (opts.focus=="first") {
						window.setTimeout(function() {
							//console.log($newTr.find("td").eq(0));
							$newTr.find("td").each(function() {
								var col = getColumnInfo(this);
								/// Skip underscored names
								if (col.name.search(/^_.*_$/)==-1) {
									$(this).click();
									return false
								}
							});
						}, 50);
					}
					else {
						$newTr.find(opts.focus).click();
					}
				}
				else {
					$newTr.find("td:empty").each(function() {
						if (!getColumnInfo(this).readonly) {
							$(this).click();
							return false;
						}
					});
				}
				return $newTr;
			},

			scrollToRow: function(rowRef) {
				var $rowRef = this.getRow(rowRef);
				if ($rowRef.offset().top > $(window).scrollTop() + $(window).height()
					|| $rowRef.offset().top + $rowRef.height() < $(window).scrollTop()) {
					$('html,body').animate({
						scrollTop: $rowRef.offset().top > 40 ? $rowRef.offset().top - 40 : $rowRef.offset().top
					}, 300);
				}
			},

			getFields: function() {
				/// Cache (no updates to fields possible once defined; add if needed)
				if (this._fields)  return this._fields;

				var $hdr = getHeaderRow(this.$table);
				/// Primary key
				var pkName = getHeaderRow(this).data("pkName");
				/// Hidden fields
				var hiddenFields = $hdr.data("hidden-fields");
				/// Visible fields
				var visibleFields = [];
				$hdr.find("th").each(function() {
					var col = getColumnInfo(this);
					if (!col.readonly && col.handler.get) {
						visibleFields.push(col.name);
					}
				});

				this._fields = [];
				if (pkName)  this._fields.push(pkName);
				if (hiddenFields)  this._fields = this._fields.concat(hiddenFields);
				this._fields = this._fields.concat(visibleFields);
				return this._fields;
			},

			getCell: function(rowRef, colRef) {
				/// For getValue({row: 2, col: 4}) calls
				if (rowRef && !colRef && typeof(rowRef)=="object"
					&& typeof(rowRef.row)!="undefined" && typeof(rowRef.col)!="undefined") {
					colRef = rowRef;
				}
				else if (colRef && typeof(colRef)=="object") {
					if (typeof(colRef.col)!="undefined") {
						colRef = colRef.col;
					}
					else if ($(colRef)[0].tagName == "TD") {
						return $(colRef);
					}
				}
				/// assume string or number
				var $row = this.getRow(rowRef);
				/// FIX: Should speed this up at some point
				var $cell = null;
				$row.find("td").each(function() {
					var colInfo = getColumnInfo(this);
					if (colInfo.name == colRef) {
						$cell = $(this);
						return;
					}
					if (colInfo.index == colRef) {
						$cell = $(this);
						return;
					}
				});
				return $cell;
			},

			//rowRef: can be a row or a cell (in which case, don't pass colRef)
			getValue: function(rowRef, colRef) {
				/// For getValue({row: 2, col: 4}) calls
				if (rowRef && !colRef && typeof(rowRef)=="object" && rowRef.row && rowRef.col) {
					colRef = rowRef;
				}
				/// Check if rowRef is TD
				else if ($(rowRef).length && $(rowRef)[0].tagName=="TD") {
					colRef = rowRef;
					rowRef = this.getRow(rowRef);
				}
				var hiddenVals = this.getRow(rowRef).data("hidden");
				if (hiddenVals && hiddenVals[colRef] !== undefined) {
					return hiddenVal;
				}
				else {
					var $cell = this.getCell(rowRef, colRef);
					var colInfo = getColumnInfo($cell);
					return colInfo.handler.get ? colInfo.handler.get($cell) : $cell.text();
				}
			},

			//rowRef: can be a row or a cell (in which case, don't pass colRef)
			//        or a {row: <row>, col: <col>} object (in which case, don't pass colRef)
			setValue: function(rowRef, colRef, value) {
				/// For setValue({row: 2, col: 4}, value) calls
				if (rowRef && !colRef && typeof(rowRef)=="object" && rowRef.row && rowRef.col) {
					value = colRef;
					colRef = rowRef;
				}
				/// Check if rowRef is TD
				else if ($(rowRef).length && $(rowRef)[0].tagName=="TD") {
					value = colRef;
					colRef = rowRef;
					rowRef = this.getRow(rowRef);
				}
				var hiddenObj = this.getRow(rowRef).data("hidden");
				if (hiddenObj && hiddenObj[colRef] !== undefined) {
					hiddenObj[colRef] = value;
				}
				else {
					var $cell = this.getCell(rowRef, colRef);
					var colInfo = getColumnInfo($cell);
					colInfo.handler.set($cell, value);
				}
			},

			getRecord: function(pk) {
				var record = {};
				this.getRow(pk).each(function() {
					var data_hidden = $(this).data("hidden");
					for (var k in data_hidden) {
						record[k] = data_hidden[k];
					}
					/// If this table had a primary key specified, put it into the record
					var pkName = getHeaderRow(this).data("pkName");
					if (pkName) {
						var data_pk = $(this).data("pk");
						record[getHeaderRow(this).data("pkName")] = data_pk;
					}
				}).find("td").each(function() {
					var col = getColumnInfo(this);
					/// Ignore: readonly, handler's with no get and don't overwrite existing
					if (!col.readonly && col.handler.get && !record[col.name]) {
						record[col.name] = col.handler.get($(this));
					}
				});
				return record;
			},

			find: function(criteria, opts) {
				var m = this;
				var rowMatch = null;
				var $trs = this.$table.find("tr[data-pk]");
				for (var i=0; i<$trs.length; i++) {
					var el = $trs[i];
					var match = true;
					for (var key in criteria) {
						var val = criteria[key];

						if (m.getValue(el, key) != val) {
							match = false;
							break;
						}
					}
					if (match) {
						rowMatch = el;
						break;
					}
				}
				return rowMatch ? $(rowMatch) : null;
			},

			collectChangeset: function() {
				var pkName = getHeaderRow(this).data("pkName");
				/// If no primary key specified, then changes can't be handled properly,
				/// so mark all records as new and submit
				if (!pkName)  this.markAllAsNew();

				var deleted = [], changed = {}, inserted = [];

				for (var pk in this.deleted)  deleted.push(pk);

				for (var pk in this.inserted) {
					if (!this.deleted[pk]) {
						inserted.push(this.getRecord(pk));
					}
				}

				for (var pk in this.changed) {
					if (!this.deleted[pk] && !this.inserted[pk]) {
						changed[pk] = this.getRecord(pk);
					}
				}

				var tableChanges = {
					deleted: deleted,
					changed: changed,
					inserted: inserted
				};

				return tableChanges;
			},
			collectJsonTable: function() {
				var records = {headers: [], data: []};

				records.headers = this.getFields();
				console.log(records.headers);

				var _this = this;
				this.getDataRows().each(function() {
					var newRow = [];
					for (var i=0; i<records.headers.length; i++) {
						newRow.push(_this.getValue(this, records.headers[i]));
					}
					records.data.push(newRow);
				});

				return records;
			},

			collect: function() {
				if (this.$table.data("format") == "json-table") {
					return this.collectJsonTable();
				}
				else {
					return this.collectChangeset();
				}
			},

			getDataRows: function() {
				return this.$table.find("> tbody > tr:not(.notData)").filter(function() {
					return this.cells[0].tagName == "TD";
				});
			},

			markAllAsNew: function() {
				this.deleted = [];
				this.changed = {};
				this.inserted = [];
				this.lastNewPk = 0;
				var _this = this;
				this.getDataRows().each(function() {
					$(this).attr("data-pk", "_new_"+_this.lastNewPk);
					_this.inserted["_new_"+_this.lastNewPk] = true;
					_this.lastNewPk++;
				});
			},
			ajaxSubmit: function(callback) {
				$widget.find('.changes').val(
					JSON.stringify($widget.data("manager").collect())
				);
				$widget.closest("form").ajaxSubmit(function(data) {
					$widget.data("manager").saveDone();
					if (callback)  callback(data);
				});
			},
			/// XXX I think what I really need to do is re-GET the row, but
			/// I have no generic way of doing that. Instead, need to update
			/// every reference to the primary key that occurs in the row!
			/// XXX I just know this is going to get me into trouble!
			ajaxFormDone: function(data) {
				var jsonData = JSON.parse(data);
				if (jsonData && jsonData.pkChanges) {
					for (var oldPk in jsonData.pkChanges) {
						var newPk = jsonData.pkChanges[oldPk];
						var $tr = $widget.data("manager").getRow(oldPk);
						$tr.attr("data-pk", newPk).data("pk", newPk);
						$tr.find("input.rowselect").val(newPk);
					}
				}
			}
		});
		$(this).data("manager", $(this).closest(".widget").data("manager"));
		/// For backwards compat.
		$(this).data("editor", $(this).closest(".widget").data("manager"));

		$table.on("change blur", function(event) { return $table.data("editor").changeRow(event.target) });

		$table.keypress(function(event) {
			if (event.which==13 && event.target.tagName == "INPUT") {
				event.preventDefault();
				return false;
			}
		});

		$table.find("th").each(function() {
			var $th = $(this);
			var colInfo = getColumnInfo($th);
			if (!colInfo.handler) {
				if (colInfo.readonly)  return;
				//onsole.debug(colInfo);
				throw "TableEditor error: No handler set for column type '"+colInfo.$th.data("handler")+"' on column '"+colInfo.name+"'";
			}
			if (colInfo.handler.init) {
				var ret = colInfo.handler.init($th);
				/// If the init function returns something,
				/// make that the new handler
				if (ret) {
					//onsole.debug("setting handler", colInfo);
					colInfo.handler = ret;
				}
			}
		});

		/** Disable drag and drop rearrangements
		var dragging = null;
		var $matchingTr = null;
		var $insertIndicator = $("<div class=insertIndicator>");
		var insertAbove = true;
		$table.find("td:first-of-type")
			.mousedown(function(event) {
				dragging = $(this).closest("tr")[0];
				$(document.body).append($insertIndicator);
			});

		$(window).mousemove(function(event) {
			if (dragging) {
				var el = document.elementFromPoint(event.pageX, event.pageY);
				var $tr = $matchingTr = $(el).closest("tr");
				if ($tr.length) {
					if (Math.abs(event.pageY - $tr.offset().top)
						< Math.abs(event.pageY - ($tr.offset().top + $tr.height())) ) {
						$insertIndicator
							.css("top", $tr.offset().top)
							.css("left", $tr.offset().left)
						insertAbove = true;
					}
					else {
						$insertIndicator
							.css("top", $tr.offset().top + $tr.height())
							.css("left", $tr.offset().left);
						insertAbove = false;
					}
				}
			}
		}).mouseup(function(event) {
			if (dragging) {
				//onsole.debug("y",$matchingTr);
				if ($matchingTr && $matchingTr.length) {
					//onsole.debug("x",$matchingTr);
					if (insertAbove) {
						//onsole.debug("z",$matchingTr, dragging);
						$matchingTr.before(dragging);
					}
					else {
						//onsole.debug("a",$matchingTr, dragging);
						$matchingTr.after(dragging);
					}
				}
				dragging = null;
				$insertIndicator.remove();
			}
		});
		**/

		$(window).scroll(function() {
			/// FIX: Doesn't handle the horizontal
			var $controls = $widget.find(".controls:not(.clone)");
			var $controlsParent = $controls.parent();
			var $controls_bottom = $controls.offset().top;
			var $controlsParent_top = $controlsParent.offset().top;
			var $controlsParent_bottom = $controlsParent_top + $controlsParent.height() - $controls.height();
			//onsole.debug($controls_bottom, $controlsParent_top, $controlsParent_bottom, $(window).scrollTop());
			if (!$controls.data("fixed")) {
				if ($controls_bottom < $(window).scrollTop()
					&& $controlsParent_bottom > $(window).scrollTop()) {
					$controls.after( $controls.clone().addClass("clone") );
					$controls.css("width", $controls.width()).addClass("fixed");
					$controls.data("fixed", true);
				}
			}
			else if ($controls.data("fixed")) {
				if ($controlsParent_top >= $(window).scrollTop()
					|| $controlsParent_bottom <= $(window).scrollTop()) {
					//onsole.debug("Xxxxx");
					$controls.css("width","").removeClass("fixed");
					$controls.data("fixed", false);
					$controls.parent().find(".controls.clone").remove();
				}
			}
		});
		$(window).on("beforeunload", function() {
			if ($widget.data("manager").hasChanges()) {
				return "Table data not saved yet";
			}
		});

		$widget.closest("form").submit(function() {
			var formControl = $widget.data("formControl") || getManager($widget).$table.data("formControl");
			$widget.find('[name='+formControl+'], .changes').val(
				JSON.stringify($widget.data("manager").collect())
			);
			$widget.data("manager").saveDone();
		});

		function rowIndex(td) {
			return $(td).closest("tr")[0].rowIndex;
		}

		/* Copying */
		var lastClicked = null;
		$widget.on("mousedown", "tr:not(.header):not(.notData) td", function(event) {
			var td = $(event.target).closest("td")[0];
			if (lastClicked && event.shiftKey) {
				event.stopPropagation();
				event.preventDefault();
				var lastClickedCol = getColumnInfo(lastClicked);
				var col = getColumnInfo(td);
				/// Make sure it has get/set methods and the name's are equal
				if (col.handler.get && col.handler.get && col.name == lastClickedCol.name) {
					var delta = rowIndex(td) > rowIndex(lastClicked) ? 1 : -1;
					for (var i = rowIndex(lastClicked); i!=rowIndex(td)+delta; i+=delta) {
						var $tr = $(td).closest("table").find("tr").eq(i);
						if (!$tr.hasClass("header") && !$tr.hasClass("notData")) {
							col.handler.set($($tr[0].cells[td.cellIndex]), col.handler.get($(lastClicked)));
							$widget.data("manager").changeRow($tr[0]);
						}
					}
				}
			}
			lastClicked = td;
		});
	});

	function clearEditing(el) {
		if (!el || (el.jquery && el.length==0)) return;
		var col = getColumnInfo(el);
		/// XXX This is a hack. Need to see if anything that could indicate
		/// the row has changed, does indicate that the row has changed.
		$(el).find("input, textarea, select").blur();
		$(el)
			.removeClass("table_editing")
			.applyFunction(col.handler.view.bind(col.handler));
	}

	$editTables.find("th").each(function() {
		var col = getColumnInfo(this);
		$(this).closest("table.editable").find("tr").each(function() {
			$(this).find("td:nth("+col.index+"),th:nth("+col.index+")").addClass("field-"+col.name);
		});
	});

	$editTables.on("click", "td", function(event) {
		if (!$(this).hasClass("table_editing")) {
			var col = getColumnInfo(this);
			if (!col.readonly && col.handler.edit) {
				clearEditing( $(this).closest("table.editable").find(".table_editing") );
				var retVal = col.handler.edit( $(this).addClass("table_editing") );
				if (retVal === null) {
					event.stopPropagation();
					event.preventDefault();
				}
			}
		}
	});

	$editTables.on("keydown", "td", function(event) {
		var KEYLEFT = 37;
		var KEYUP = 38;
		var KEYRIGHT = 39;
		var KEYDOWN = 40;
		var TAB = 9;

		if (event.which == TAB) {
			event.stopPropagation();
			event.preventDefault();
			var $el = $(this);
			while ($el.length) {
				if (event.shiftKey) {
					if ($el.prev().length)  $el = $el.prev();
					else                    $el = $el.closest("tr").prev().find("td:last");
				}
				else {
					if ($el.next().length)  $el = $el.next();
					else                    $el = $el.closest("tr").next().find("td:first");
				}
				var col = getColumnInfo($el);
				if (!col.readonly) {
					$el.click();
					break;
				}
			}
		}
		/*else if (event.which == KEYDOWN) {
			$(this).closest("tr").next().find("td:nth("+$(this).index()+")").click();
		}
		else if (event.which == KEYUP) {
			$(this).closest("tr").prev().find("td:nth("+$(this).index()+")").click();
		}*/
	});

	$(window).on("mousedown", function(event) {
		if ($(".table_editing").length==0)  return;
		if (event.which == 1 && $(event.target).closest(".editable").find(".table_editing").length==0) {
			clearEditing( $(".table_editing") );
		}
	});
}
$(window).ready(setupEditableTables);

/// Hack for IE < 9 (basically IE8 only, since it's the last version on XP)
var els = ["article", "header", "footer"];
for (var i in els) {
	document.createElement(els[i]);
}

/// From http://phpjs.org/functions/date:380
function phpDate(format, timestamp) {
    // http://kevin.vanzonneveld.net
    // +   original by: Carlos R. L. Rodrigues (http://www.jsfromhell.com)
    // +      parts by: Peter-Paul Koch (http://www.quirksmode.org/js/beat.html)
    // +   improved by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
    // +   improved by: MeEtc (http://yass.meetcweb.com)
    // +   improved by: Brad Touesnard
    // +   improved by: Tim Wiel
    // +   improved by: Bryan Elliott
    //
    // +   improved by: Brett Zamir (http://brett-zamir.me)
    // +   improved by: David Randall
    // +      input by: Brett Zamir (http://brett-zamir.me)
    // +   bugfixed by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
    // +   improved by: Brett Zamir (http://brett-zamir.me)
    // +   improved by: Brett Zamir (http://brett-zamir.me)
    // +   improved by: Theriault
    // +  derived from: gettimeofday
    // +      input by: majak
    // +   bugfixed by: majak
    // +   bugfixed by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
    // +      input by: Alex
    // +   bugfixed by: Brett Zamir (http://brett-zamir.me)
    // +   improved by: Theriault
    // +   improved by: Brett Zamir (http://brett-zamir.me)
    // +   improved by: Theriault
    // +   improved by: Thomas Beaucourt (http://www.webapp.fr)
    // +   improved by: JT
    // +   improved by: Theriault
    // +   improved by: Rafal Kukawski (http://blog.kukawski.pl)
    // +   bugfixed by: omid (http://phpjs.org/functions/380:380#comment_137122)
    // +      input by: Martin
    // +      input by: Alex Wilson
    // +   bugfixed by: Chris (http://www.devotis.nl/)
    // %        note 1: Uses global: php_js to store the default timezone
    // %        note 2: Although the function potentially allows timezone info (see notes), it currently does not set
    // %        note 2: per a timezone specified by date_default_timezone_set(). Implementers might use
    // %        note 2: this.php_js.currentTimezoneOffset and this.php_js.currentTimezoneDST set by that function
    // %        note 2: in order to adjust the dates in this function (or our other date functions!) accordingly
    // *     example 1: date('H:m:s \\m \\i\\s \\m\\o\\n\\t\\h', 1062402400);
    // *     returns 1: '09:09:40 m is month'
    // *     example 2: date('F j, Y, g:i a', 1062462400);
    // *     returns 2: 'September 2, 2003, 2:26 am'
    // *     example 3: date('Y W o', 1062462400);
    // *     returns 3: '2003 36 2003'
    // *     example 4: x = date('Y m d', (new Date()).getTime()/1000);
    // *     example 4: (x+'').length == 10 // 2009 01 09
    // *     returns 4: true
    // *     example 5: date('W', 1104534000);
    // *     returns 5: '53'
    // *     example 6: date('B t', 1104534000);
    // *     returns 6: '999 31'
    // *     example 7: date('W U', 1293750000.82); // 2010-12-31
    // *     returns 7: '52 1293750000'
    // *     example 8: date('W', 1293836400); // 2011-01-01
    // *     returns 8: '52'
    // *     example 9: date('W Y-m-d', 1293974054); // 2011-01-02
    // *     returns 9: '52 2011-01-02'
    var that = this,
        jsdate, f, formatChr = /\\?([a-z])/gi,
        formatChrCb,
        // Keep this here (works, but for code commented-out
        // below for file size reasons)
        //, tal= [],
        _pad = function (n, c) {
            if ((n = n + '').length < c) {
                return new Array((++c) - n.length).join('0') + n;
            }
            return n;
        },
        txt_words = ["Sun", "Mon", "Tues", "Wednes", "Thurs", "Fri", "Satur", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    formatChrCb = function (t, s) {
        return f[t] ? f[t]() : s;
    };
    f = {
        // Day
        d: function () { // Day of month w/leading 0; 01..31
            return _pad(f.j(), 2);
        },
        D: function () { // Shorthand day name; Mon...Sun
            return f.l().slice(0, 3);
        },
        j: function () { // Day of month; 1..31
            return jsdate.getDate();
        },
        l: function () { // Full day name; Monday...Sunday
            return txt_words[f.w()] + 'day';
        },
        N: function () { // ISO-8601 day of week; 1[Mon]..7[Sun]
            return f.w() || 7;
        },
        S: function () { // Ordinal suffix for day of month; st, nd, rd, th
            var j = f.j();
            return j < 4 | j > 20 && ['st', 'nd', 'rd'][j%10 - 1] || 'th';
        },
        w: function () { // Day of week; 0[Sun]..6[Sat]
            return jsdate.getDay();
        },
        z: function () { // Day of year; 0..365
            var a = new Date(f.Y(), f.n() - 1, f.j()),
                b = new Date(f.Y(), 0, 1);
            return Math.round((a - b) / 864e5) + 1;
        },

        // Week
        W: function () { // ISO-8601 week number
            var a = new Date(f.Y(), f.n() - 1, f.j() - f.N() + 3),
                b = new Date(a.getFullYear(), 0, 4);
            return _pad(1 + Math.round((a - b) / 864e5 / 7), 2);
        },

        // Month
        F: function () { // Full month name; January...December
            return txt_words[6 + f.n()];
        },
        m: function () { // Month w/leading 0; 01...12
            return _pad(f.n(), 2);
        },
        M: function () { // Shorthand month name; Jan...Dec
            return f.F().slice(0, 3);
        },
        n: function () { // Month; 1...12
            return jsdate.getMonth() + 1;
        },
        t: function () { // Days in month; 28...31
            return (new Date(f.Y(), f.n(), 0)).getDate();
        },

        // Year
        L: function () { // Is leap year?; 0 or 1
            var j = f.Y();
            return j%4==0 & j%100!=0 | j%400==0;
        },
        o: function () { // ISO-8601 year
            var n = f.n(),
                W = f.W(),
                Y = f.Y();
            return Y + (n === 12 && W < 9 ? 1 : n === 1 && W > 9 ? -1 : 0);
        },
        Y: function () { // Full year; e.g. 1980...2010
            return jsdate.getFullYear();
        },
        y: function () { // Last two digits of year; 00...99
            return (f.Y() + "").slice(-2);
        },

        // Time
        a: function () { // am or pm
            return jsdate.getHours() > 11 ? "pm" : "am";
        },
        A: function () { // AM or PM
            return f.a().toUpperCase();
        },
        B: function () { // Swatch Internet time; 000..999
            var H = jsdate.getUTCHours() * 36e2,
                // Hours
                i = jsdate.getUTCMinutes() * 60,
                // Minutes
                s = jsdate.getUTCSeconds(); // Seconds
            return _pad(Math.floor((H + i + s + 36e2) / 86.4) % 1e3, 3);
        },
        g: function () { // 12-Hours; 1..12
            return f.G() % 12 || 12;
        },
        G: function () { // 24-Hours; 0..23
            return jsdate.getHours();
        },
        h: function () { // 12-Hours w/leading 0; 01..12
            return _pad(f.g(), 2);
        },
        H: function () { // 24-Hours w/leading 0; 00..23
            return _pad(f.G(), 2);
        },
        i: function () { // Minutes w/leading 0; 00..59
            return _pad(jsdate.getMinutes(), 2);
        },
        s: function () { // Seconds w/leading 0; 00..59
            return _pad(jsdate.getSeconds(), 2);
        },
        u: function () { // Microseconds; 000000-999000
            return _pad(jsdate.getMilliseconds() * 1000, 6);
        },

        // Timezone
        e: function () { // Timezone identifier; e.g. Atlantic/Azores, ...
            // The following works, but requires inclusion of the very large
            // timezone_abbreviations_list() function.
/*              return that.date_default_timezone_get();
*/
            throw 'Not supported (see source code of date() for timezone on how to add support)';
        },
        I: function () { // DST observed?; 0 or 1
            // Compares Jan 1 minus Jan 1 UTC to Jul 1 minus Jul 1 UTC.
            // If they are not equal, then DST is observed.
            var a = new Date(f.Y(), 0),
                // Jan 1
                c = Date.UTC(f.Y(), 0),
                // Jan 1 UTC
                b = new Date(f.Y(), 6),
                // Jul 1
                d = Date.UTC(f.Y(), 6); // Jul 1 UTC
            return 0 + ((a - c) !== (b - d));
        },
        O: function () { // Difference to GMT in hour format; e.g. +0200
            var tzo = jsdate.getTimezoneOffset(),
                a = Math.abs(tzo);
            return (tzo > 0 ? "-" : "+") + _pad(Math.floor(a / 60) * 100 + a % 60, 4);
        },
        P: function () { // Difference to GMT w/colon; e.g. +02:00
            var O = f.O();
            return (O.substr(0, 3) + ":" + O.substr(3, 2));
        },
        T: function () { // Timezone abbreviation; e.g. EST, MDT, ...
            // The following works, but requires inclusion of the very
            // large timezone_abbreviations_list() function.
/*              var abbr = '', i = 0, os = 0, default = 0;
            if (!tal.length) {
                tal = that.timezone_abbreviations_list();
            }
            if (that.php_js && that.php_js.default_timezone) {
                default = that.php_js.default_timezone;
                for (abbr in tal) {
                    for (i=0; i < tal[abbr].length; i++) {
                        if (tal[abbr][i].timezone_id === default) {
                            return abbr.toUpperCase();
                        }
                    }
                }
            }
            for (abbr in tal) {
                for (i = 0; i < tal[abbr].length; i++) {
                    os = -jsdate.getTimezoneOffset() * 60;
                    if (tal[abbr][i].offset === os) {
                        return abbr.toUpperCase();
                    }
                }
            }
*/
            return 'UTC';
        },
        Z: function () { // Timezone offset in seconds (-43200...50400)
            return -jsdate.getTimezoneOffset() * 60;
        },

        // Full Date/Time
        c: function () { // ISO-8601 date.
            return 'Y-m-d\\TH:i:sP'.replace(formatChr, formatChrCb);
        },
        r: function () { // RFC 2822
            return 'D, d M Y H:i:s O'.replace(formatChr, formatChrCb);
        },
        U: function () { // Seconds since UNIX epoch
            return jsdate / 1000 | 0;
        }
    };
    this.date = function (format, timestamp) {
        that = this;
        jsdate = (timestamp == null ? new Date() : // Not provided
            (timestamp instanceof Date) ? new Date(timestamp) : // JS Date()
            new Date(timestamp * 1000) // UNIX timestamp (auto-convert to int)
        );
        return format.replace(formatChr, formatChrCb);
    };
    return this.date(format, timestamp);
}

/** Dialogs **/

function popupDialog($a, opts) {
	var opts = opts || {};
	opts.buttons = opts.buttons || [];
	opts.className = opts.className || "";

	var $veil = $("<div class=veil>")
		.appendTo($("body"));
	/// immediately setting opacity=0 and using requestAnimFrame
	/// doesn't trigger css animation in fx...
	setTimeout(function() {
		$veil.css('opacity',1);
	}, 0);

	/// Embed dialog into the veil
	
	/// $a could be a string, element or jquery element
	$a = $("<div class=dialog>")
		.addClass(opts.className)
		.html($a)
		.appendTo($veil);

	/// Add controls
	$a.append($('<div class=controls>').append(opts.buttons));

	$a.data("veil", $veil);
	
	return $a;
}

function reportError(msg) {
	popupDialog(msg+"<div class=controls><button type=button onclick=dismissDialogs()>OK</button></div>");
}

function dismissDialog($a, callback) {
	$a.data("veil").css('opacity',0);
	setTimeout(function() {
		$a.data("veil").remove();
	}, 500);
}

function dismissDialogs(callback) {
	var first = true;
	var $dialogs = $();
	$(".dialog:visible").each(function() {
		$dialogs.add(dismissDialog($(this), first ? callback : null));
		first = false;
	});
}

function nyi() {
	popupDialog('Not yet implemented :(', {buttons:[
		$('<button type=button>OK</button>').click(dismissDialogs),
	]});
}

function popupEditDialog($content, opts) {
	var whatsDirty = {};
	popupDialog($content, {
		className: 'contextMenu '+opts.className,
		buttons: [
			$('<button type=button class=saveButton disabled>').html('Save').on('click', function() {
				$(".dialog .saveButton")[0].disabled = true;
				console.log(whatsDirty);
				var controls = opts.controls;
				for (var control in controls) {
					if (whatsDirty[control]) {
						whatsDirty[control] = false;
						if ($('.dialog *[data-control='+control+']').is('input, select, textarea')) {
							//var valid = $('.dialog *[data-control='+control+']').get().map(a=>$(a).is(':valid')).reduce((a,b)=>a && b);
							var valid = $('.dialog *[data-control='+control+']').get().map(function(a){return $(a).is(':valid')}).reduce(function(a,b){return a && b});
							if (valid) {
								var $control = $('.dialog *[data-control='+control+']');
								var val = $control.val();
								/// 'false' specifically means change didn't save
								if (controls[control].change(val, $control)===false) {
									$(".dialog .saveButton")[0].disabled = false;
									whatsDirty[control] = true;
								}
							}
						}
						else {
							/// Non-standard control, just call with no arguments

							/// 'false' specifically means change didn't save
							if (controls[control].change($('.dialog *[data-control='+control+']'))===false) {
								$(".dialog .saveButton")[0].disabled = false;
								whatsDirty[control] = true;
							}
						}
					}
				}
			}),
			$('<button type=button class=closeButton>').html('Close').on('click', dismissDialogs),
		],
	});
	$(".dialog").on("change keyup", function(event) {
		if ($(event.target).closest('*[data-control]').length) {
			var name = $(event.target).closest('*[data-control]').data('control');
			whatsDirty[name] = true;
		}
		$(".dialog .saveButton")[0].disabled = false;
	});
}
/** End Dialogs **/



/// The above makes the assumption that tables are completely managed. Sometimes, we just want some of the features
/// from the above. Below is an attempt to handle that.
class TableManager {
	constructor(table) {
		this.table = table;
		
		/// Find header row
		let tr = table.querySelector('thead tr, tr.header');
		if (!tr) {
			let th = table.querySelector('th[data-field]');
			if (th)  tr = th.closest('tr');
		}
		
		/// Determine header information
		let ths = tr.querySelectorAll('th');
		this.fieldIds = [];
		this.fieldLabels = [];
		this.readOnly = new Set();
		for (let th of ths) {
			if (th.dataset.field) {
				this.fieldIds.push(th.dataset.field);
			}
			else {
				this.fieldIds.push(th.textContent);
			}
			this.fieldLabels.push(th.textContent);
			
			if (th.dataset.readonly && th.dataset.readonly == 'readonly') {
				this.readOnly.add(this.fieldIds[this.fieldIds.length-1]);
			}
		}
		this.fieldIdIndexes = Object.fromEntries(this.fieldIds.map((v,i) => [v,i]));
		
		this.handlers = {};
		
		/// To validate the table (e.g. before submission). Can update GUI.
		this.validators = [];
	}
	
	get numRows() {
		return this.getRows().length;
	}
	
	get numColumns() {
		return this.fieldIds.length;
	}
	
	getRows() {
		return [...this.table.querySelectorAll('tbody tr:not(.header)')];
	}
	
	getRow(rowRef) {
		let val = null;
		
		if (rowRef && rowRef instanceof HTMLElement) {
			return rowRef.closest('tr');
		}
		else if (typeof(rowRef)=='number') {
			rowRef = rowRef < 0 ? this.numRows+rowRef : rowRef;
			val = this.getRows()[rowRef];
		}
		else if (typeof(rowRef)=='object') {
			let allRows = this.getRows();
			for (let row of allRows) {
				let match = true;
				for (let [field,value] of Object.entries(rowRef)) {
					let cell = this.getCell(row, field);
					if (cell.textContent != value) {
						match = false;
						break;
					}
				}
				if (match) {
					return row;
				}
			}
		}
		
		return val;
	}
	
	/// Since the DOM has no notion of a column element (virtual or otherwise),
	/// we have to settle for indexes.
	getColumnIndex(colRef) {
		if (colRef && colRef instanceof HTMLElement) {
			return colRef.closest('th, td').cellIndex;
		}
		else if (typeof(colRef)=='number') {
			return colRef;
		}
		/// If string, assume field id of column
		else if (typeof(colRef)=='string') {
			return this.fieldIdIndexes[colRef];
		}
		
		return null;
	}
	
	getCell(rowRef, cellRef) {
		let row = this.getRow(rowRef);
		let colIndex = this.getColumnIndex(cellRef);
		
		return row.cells[colIndex];
	}
	
	getColumnCells(cellRef) {
		return this.getRows().map(row => this.getCell(row, cellRef));
	}
	
	getValue(rowRef, cellRef) {
		let row = this.getRow(rowRef);
		let cell = this.getCell(row, cellRef);
		if (!cell)  return null;
		
		/// Replace with handler
		for (let handler of Object.values(tableManagerHandlers)) {
			if (handler.test(cell)) {
				return handler.get(cell);
			}
		}
		/// No handler? just return text (excluding class=exclude)
		let tempCell = cell.cloneNode(true);
		tempCell.querySelectorAll('.exclude').forEach(el => el.remove());
		return tempCell.textContent;
	}
	
	getColumnValues(cellRef) {
		return this.getRows().map(row => this.getValue(row, cellRef));
	}
	
	getTableValues(o = {}) {
		//o.includeReadOnly = false
		let tableValues = {fields: this.fieldIds.filter(field => !this.readOnly.has(field)), data: []};
		
		let rows = this.getRows();
		for (let row of rows) {
			let dataRow = tableValues.fields.map(field => this.getValue(row, field));
			tableValues.data.push(dataRow);
		}
		
		return tableValues;
	}
	
	/// rowRef, cellRef1, value1, cellRef2, value2, etc.
	setValue(rowRef, ...args) {
		this.setInnerValue(rowRef, null, ...args);
	}
	
	setInnerValue(rowRef, selector, ...args) {
		for (let i=0; i<args.length; i+=2) {
			let cellRef = args[i];
			let value = args[i+1];
			let row = this.getRow(rowRef);
			console.log(row, cellRef)
			let cellContent = this.getCell(row, cellRef);
			if (selector) {
				cellContent = cellContent.querySelector(selector);
			}
			/// Replace with handler
			cellContent.textContent = value;
		}
	}
	
	addEventListenerRow(rowRef, eventName, eventFunc) {
		this.getRow(rowRef).addEventListener(eventName, eventFunc);
	}
	
	addEventListenerColumn(colRef, eventName, eventFunc) {
		let colIndex = this.getColumnIndex(colRef);
		this.table.addEventListener(eventName, (...args) => {
			if (args[0].target.closest('td,th')?.cellIndex === colIndex) {
				eventFunc(...args);
			}
		});
	}
	
	findRows(criteria) {
		let rows = this.getRows();
		let found = [];
		
		/// Prepare criteria
		let _criteria = criteria;
		criteria = {};
		for (let field in _criteria) {
			if (typeof(_criteria[field])=='string' || typeof(_criteria[field])=='number') {
				criteria[field] = (value, row) => String(value) === String(_criteria[field]);
			}
			else if (_criteria[field] instanceof RegExp) {
				criteria[field] = (value, row) => _criteria[field].test(value);
			}
			/// Otherwise, we got a custom test
			else if (_criteria[field] instanceof Function) {
				criteria[field] = _criteria[field];
			}
		}
		
		for (let row of rows) {
			let match = true;
			for (let [field,test] of Object.entries(criteria)) {
				if (!test(this.getValue(row, field), row)) {
					match = false;
					break;
				}
			}
			if (match) {
				found.push(row);
			}
		}
		
		return found;
	}
	
	insertRow(row, pos = null) {
		let tr = null;
		if (row instanceof HTMLElement) {
			tr = row;
		}
		else {
			tr = document.createElement('tr');
			let insertOrder = [];
			let extras = {};
			for (let [field,val] of Object.entries(row)) {
				let index = this.fieldIdIndexes[field];
				if (index !== undefined) {
					insertOrder[index] = val;
				}
				else {
					extras[field] = val;
				}
			}
			tr.dataset.extras = JSON.stringify(extras);
			for (let val of insertOrder) {
				if (val !== undefined) {
					let td = document.createElement('td');
					td.textContent = val;
					tr.append(td);
				}
				else {
					tr.append(document.createElement('td'));
				}
			}
		}
		
		if (pos === null) {
			this.table.querySelector('tbody').append(tr);
		}
		else {
			this.getRow(pos).before(tr);
		}
		
		return tr;
	}
	
	/// checks for all failures, and messages them all
	validate() {
		let msgs = [];
		for (let validFunc of this.validators) {
			let result = validFunc(this);
			if (typeof(result)=='string') {
				msgs.push(result);
			}
			else if (Array.isArray(result)) {
				msgs.push(...result);
			}
		}
		
		if (msgs.length) {
			popupDialog([
				n('h2', 'Errors in parameters'),
				n('ul',
					msgs.map(msg => n('li', msg)),
				),
			], {buttons: [
				n('button', 'OK', {on:{click:dismissDialogs}}),
			]});
			return false;
		}
		
		return true;
	}
}

/** Work in progress */
var tableManagerHandlers = {
	checkbox: {
		create: function(col, newTr) {
			return n('td', {class: "field-"+col.name},
				n('input', {type: 'checkbox'})
			);
		},
		test(td) {
			return Boolean(td.querySelector('input[type=checkbox]'));
		},
		edit: function(td) {
			return false;
		},
		view: function(td) {
			return false;
		},
		get: function(td) {
			if (td.querySelector("input")) {
				return Boolean(td.querySelector("input").checked);
			}
			return false;
		},
		set: function(td, val) {
			if (val) {
				td.querySelector("input").checked = val;
			}
		}
	},
	select: {
		test(td) {
			return Boolean(td.querySelector('select'));
		},
		get(td) {
			if (td.querySelector('select')) {
				return td.querySelector('select').value;
			}
			return null;
		},
	},
};

function skipError(func, valIfError = null) {
	try {
		return func();
	}
	catch(e) {
		return valIfError;
	}
}

function tableManager(table) {
	let managerKey = '__tableManager12930';
	
	/// Return null if any errors
	try {
		if (!table[managerKey]) {
			table[managerKey] = new TableManager(table);
		}
		
		return table[managerKey];
	}
	catch (e) {
		console.error('Error initialising TableManager');
		e.message = 'Error initialising TableManager -> '+e.message;
		throw(e);
	}
}

/// Hack for IE < 9 (basically IE8 only, since it's the last version on XP)
var els = ["article", "header", "footer"];
for (var i in els) {
	document.createElement(els[i]);
}