/*************************************************/
/* Map stuff                                     */
/*************************************************/
var transform = null; 
var mapZoom = 1;
var mapZoomPower = 0;
function transformStr() { return 'translate('+transform.originX+'px, '+transform.originY+'px) scale('+transform.scale+') translate('+transform.offsetX+'px, '+transform.offsetY+'px) translate('+(-transform.originX)+'px, '+(-transform.originY)+'px) '; }

function setupMapControls() {
	/*function transformStr() { return 'scale('+transform.scale+') translate('+transform.offsetX+'px, '+transform.offsetY+'px)'; }
	function transformOriginStr() { return transform.originX+'px '+transform.originY+'px'; }*/
	$(document).on('wheel', '.mapViewParent', function(event) {
		if (event.originalEvent.deltaY > 0) {
			mapZoomPower -= 0.6;
		}
		else {
			mapZoomPower += 0.6;
		}
		mapZoomPower = Math.min(10, Math.max(-3.6, mapZoomPower));
		var newScreenX = event.originalEvent.clientX - $('.mapViewParent').offset().left;
		var newScreenY = event.originalEvent.clientY - $('.mapViewParent').offset().top;
		var mapX = ((newScreenX-transform.screenX)/transform.scale + transform.originX);
		var mapY = ((newScreenY-transform.screenY)/transform.scale + transform.originY);
		transform.scale = Math.pow(2, mapZoomPower);
		transform.offsetX = (newScreenX - mapX)/transform.scale;
		transform.offsetY = (newScreenY - mapY)/transform.scale;
		transform.originX = mapX;
		transform.originY = mapY;
		transform.screenX = newScreenX;
		transform.screenY = newScreenY;
		if ($("svg style").length) {
			$("svg style").each(function(i) {
				var polygonRule = this.sheet.cssRules[0];
				/// This is a bit hacky
				if (transform.borderWidth[i] === undefined) {
					transform.borderWidth[i] = parseFloat(polygonRule.style.strokeWidth);
				}
				polygonRule.style.strokeWidth = transform.borderWidth[i]/transform.scale;
			});
		}
		$('.mapViewParent').find(".mapView").css('transform', transformStr());
		//$('.mapViewParent').find(".mapView").css('transform-origin', transformOriginStr());
		return false;
	});
	var startPos = {x: null, y: null};
	$(document).on('mousedown', '.mapViewParent', function(event) {
		startPos.x = event.clientX;
		startPos.y = event.clientY;
		//onsole.log(startPos);
		$(".mapView").css('cursor', 'grabbing');
		return false;
	}).on('mousemove', '.mapViewParent', function(event) {
		if (startPos.x !== null) {
			var deltaX = (event.clientX - startPos.x)/transform.scale;
			var deltaY = (event.clientY - startPos.y)/transform.scale;
			transform.offsetX += deltaX;
			transform.offsetY += deltaY;
			transform.screenX += (event.clientX - startPos.x);
			transform.screenY += (event.clientY - startPos.y);
			startPos.x = event.clientX;
			startPos.y = event.clientY;
			//onsole.log(transformStr());
			$(this).find(".mapView").css('transform', transformStr());
			/*$(this).parent().scrollTop($(this).scrollTop()-deltaY);
			$(this).parent().scrollLeft($(this).scrollTop()-deltaX);*/
		}
		return false;
	}).on('mouseup', function(event) {
		if (startPos.x !== null) {
			//transform.zoomPointAdjustX += transform.x;
			//transform.zoomPointAdjustY += transform.y;
			startPos.x = startPos.y = null;
			$(".mapView").css('cursor', 'grab');
			return false;
		}
	});
}

function resetMapTransform() {
	mapZoom = 0;
	mapZoomPower = 0;
	transform = {
		scale: 1,
		offsetX: 0,
		offsetY: 0,
		screenX: 0,
		screenY: 0,
		originX: 0,
		originY: 0,
		borderWidth: (transform && transform.borderWidth) ? transform.borderWidth : [],
	};
}

function resetMap() {
	resetMapTransform();
	$('.mapViewParent').find(".mapView").css('transform', transformStr());
}

function zoomMap(o = {}) {
	o.step = o.step || null;
	o.reset = o.reset || null;
	/// XXX Needs fixing
	o.clientX = o.clientX || o.step < 0 ? $('.mapViewParent').offset().left : $('.mapViewParent svg').offset().left + $('.mapViewParent svg').width()/2;
	o.clientY = o.clientY || o.step < 0 ? $('.mapViewParent').offset().top : $('.mapViewParent svg').offset().top + $('.mapViewParent svg').height()/2;
	if (o.reset) {
		resetMap();
	}
	if (o.step) {
		mapZoomPower += o.step * 0.6;
		mapZoomPower = Math.min(10, Math.max(-3.6, mapZoomPower));
	}
	var newScreenX = o.clientX - $('.mapViewParent').offset().left;
	var newScreenY = o.clientY - $('.mapViewParent').offset().top;
	var mapX = ((newScreenX-transform.screenX)/transform.scale + transform.originX);
	var mapY = ((newScreenY-transform.screenY)/transform.scale + transform.originY);
	transform.scale = Math.pow(2, mapZoomPower);
	transform.offsetX = (newScreenX - mapX)/transform.scale;
	transform.offsetY = (newScreenY - mapY)/transform.scale;
	transform.originX = mapX;
	transform.originY = mapY;
	transform.screenX = newScreenX;
	transform.screenY = newScreenY;
	if ($("svg style").length) {
		$("svg style").each(function(i) {
			var polygonRule = this.sheet.cssRules[0];
			if (transform.borderWidth[i] === undefined) {
				transform.borderWidth[i] = parseFloat(polygonRule.style.strokeWidth);
			}
			polygonRule.style.strokeWidth = transform.borderWidth[i]/transform.scale;
		});
	}
	$('.mapViewParent').find(".mapView").css('transform', transformStr());
}

function toggleBorders() {
	/// Disable state tells us whether next border state should be on or off
	let bordersOff = !$('style.bordersOff')[0].disabled;
	$('style.bordersOn')[0].disabled = !bordersOff;
	$('style.bordersOff')[0].disabled = bordersOff;
}

function toggleScale(button) {
	if ($(button).text()=="Show Ranked") {
		colorPolysByRank({colorScale: 0.33});
		createLegend({ranked:true,colorScale: 0.33});
		$(button).text("Show Absolute");
	}
	else {
		colorPolys();
		createLegend();
		$(button).text("Show Ranked");
	}
}

/*************************************************/
/* END Map stuff                                 */
/*************************************************/


