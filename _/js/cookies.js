function cookieEscape(str) {
	return str.replace(/~/g, '~1').replace(/;/g, '~2');
}

function cookieUnescape(str) {
	return str.replace(/~2/g, ';').replace(/~1/g, '~');
}

var SC_PERMANENT = -1;
var SC_SESSION = -2;
function setCookie(name, value, expire, path) {
	if    (expire==SC_PERMANENT) { expire = new Date(2030,0,1); }
	else if (expire==SC_SESSION) { expire = null; }
	var str = name + "=" + cookieEscape(value)
	+ ((expire == null) ? "" : ("; expires=" + expire.toGMTString()))
	+ ((path==null)? "; path=/" : ("; path="+path));
	document.cookie = str;
	//onsole.log(str);
}

function getCookie(name) {
	if (document.cookie.length == 0) return null;
	var cookieStrs = document.cookie.split(";");
	var re = new RegExp("^\\s*"+name+"=(.*)$");
	for (var i=0; i<cookieStrs.length; i++) {
		if (  (m = cookieStrs[i].match(re))  ) {
			return cookieUnescape(m[1]);
		}
	}
	return null;
}

function yieldCookie(name, initialValue) {
	if (!hasCookie(name)) {
		setCookie(name, initialValue, SC_PERMANENT);
	}
	return getCookie(name);
}

function hasCookie(name) {
	var search = name + "=";
	if (document.cookie.length > 0) {
		if (document.cookie.indexOf(search)!=-1) {
			return true;
		}
	}
	return false;
}

function deleteCookie(name) {
	setCookie(name, "", new Date(new Date().getTime()-100));
}

