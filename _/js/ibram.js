$(document).ready(function() {
	/** Simple handler for editing isolated fields (like names/titles) **/
	var $fe = $('[data-field-edit]');
	var $value = $fe.find('.value');
	if ($value.length) {
		/// This is needed to fix Firefox issue with contenteditable on inline elements
		if (window.getComputedStyle($value[0]).getPropertyValue('display')=='inline') {
			$value.css('display', 'inline-block');
		}
		$fe.find('.value')
			.attr('contenteditable', 'true')
			.data('originalValue', $value.text())
			.on('focus', (event) => {
				$fe.append(
					$('<button class=save>')
						.text('Save')
						.on('mousedown', event => event.preventDefault())
						.on('click', async () => {
							var url = $fe.data('fieldEdit')+escape($value.text());
							await $.get(url);
							ui.message('Saved');
							$fe.find('.save').remove();
							$fe.data('originalValue', $value.text());
						})
				);
			}).on('blur', (event) => {
				//if ($(event.relatedTarget).is('.save'))  return;
				
				$fe.find('.save').remove();
				$value.text($fe.data('originalValue'));
			}).on('keypress', (event) => {
				if (event.key == 'Enter') {
					event.preventDefault();
					$fe.find('.save').click();
				}
			});
	}
	
	// handleNestedSelections();
	// handleSampleHistograms();
	// handleTimelineGraph();

	/// Map controls
	setupMapControls();
	resetMapTransform();
	
	// $('.dateSlider').each(function() {
	// 	setupDateSlider(this);
	// });
});


function viewOutput(scenarioId) {
    window.location.href = '/scenarioOutput?scenarioId='+scenarioId
}

function exportOutput(scenarioId) {
	location.href='/exportOutput?scenarioId='+scenarioId
}


async function saveScenario() {
	let saveTables = [
		'vector', 'units', 'infestationRate', 'vectorInfectionRate', 'itemInfectionRate',
		'itemVectorTransmissionRate', 'preBorderVectorDetection', 'preBorderItemDetection',
		'vectorsPerUnit', 'vectorPathwayDetection', 'itemPathwayDetection', 'vectorDailyEscapeRate',
		'itemDailyEscapeRate', 'vectorDailyMortalityRate', 'itemDailyMortalityRate',
		'vectorTransmissionRate', 'mortalityRate', 'establishmentRate', 'spreadRate',
		'eradicationRate', 'landSuitability', 'consequences', 'eradicationDetection'
	];

	let scenarioTables = {};
	for (let saveTable of saveTables) {
		let tbl = tableManager(document.querySelector(`table[data-name=${saveTable}]`));
		scenarioTables[saveTable] = tbl.getTableValues();
		if (!tbl.validate()) {
			return;
		}
	}

	ui.dialog(`<h2>Save Scenario</h2>
		<p>Changing inputs will invalidate previous runs, are you sure you want to continue?`, {
		buttons: [
			$('<button>').text('Continue').on('click', async function () {
				try {
					await $.get("/resetScenario", { scenarioId });

					const response = await $.post('/saveScenario', {
						scenarioTables: JSON.stringify(scenarioTables)
					});

					const data = skipError(() => JSON.parse(response), {});
					if (data.ok) {
						ui.dismissDialogs();
					} else {
						console.error("Save failed", data);
					}
				} catch (e) {
					console.error("Error during saveScenario:", e);
				}
			}),
			$('<button>').text('Cancel').on('click', ui.dismissDialogs)
		]
	});
}



/// Pathway page parameters
async function saveParameters() {
	let saveTables = ['climateMaps', 'items', 'pathwayPoints'];

	// let pestId = $('.toolbar').find('.pestSel').val();
	// let pathwayId = $('.toolbar').find('.pathwaySel').val();
	
	let paramTables = {};
	for (let saveTable of saveTables) {
		let tbl = tableManager(document.querySelector(`table[data-name=${saveTable}]`));
		paramTables[saveTable] = tbl.getTableValues();
		if (!tbl.validate()) {
			return;
		}
	}
	
	let ok = false;
	await new Promise(resolve => $.post('/saveParameters', {
			paramTables: JSON.stringify(paramTables),
		}, data => {
		data = skipError(_=>JSON.parse(data), {});
		//console.log(data);
		if (data.ok) {
			ok = true;
		}
	}).always(_=> resolve()));
	
	if (ok) {
		popupDialog('Saved!', {
			buttons: [
				$('<button>').text('OK').click(() => {
					dismissDialogs();
					location.reload();
				})
			]
		});
	}
	else {
		popupDialog('Failed to save', {buttons: [$('<button>').text('OK').click(dismissDialogs)] });
	}
}


function downloadParameterData(fileName) {
	const link = document.createElement('a');
	link.href = '/downloadParameterData?file=' + encodeURIComponent(fileName);
	link.download = '';
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
}

function uploadNewParameterData(fileName) {
	const input = document.createElement('input');
	input.type = 'file';
	input.accept = '.csv';
	input.onchange = () => {
		const file = input.files[0];
		if (!file) return;

		const formData = new FormData();
		formData.append('file', file);
		formData.append('fileName', fileName);

		fetch('/uploadNewParameterData', {
			method: 'POST',
			body: formData
		})
		.then(res => {
			if (!res.ok) throw new Error('Upload failed');
			alert('Upload successful');
			location.reload();
		})
		.catch(err => alert(err));
	};
	input.click();
}

function addClimateMap() {
	let mapTableMgr = tableManager($('.tabSheet[data-name=climateMaps] .dataTable')[0]);
	let $dlg = popupDialog(n('div',
		n('h2', 'Add a new climate map'),
		n('div.error'),
		n('p', 'Name: ', n('input', {name: 'name'})),
		n('p', 'Choose file: ', n('input', {type: 'file', name: 'filePicker'})),
	), {buttons: [
		n('button', 'Add', {on: {click: async event => {
			let dlg = event.target.closest('.dialog');
			let mapName = (dlg.querySelector('*[name=name]') || {}).value;
			let fileInput = dlg.querySelector('*[name=filePicker]');
			let file = fileInput?.files[0];

			
			/// Check for errors
			let errors = [];
			if (!mapName) {
				errors.push('Please specify "Name".');
			}
			if (!file) {
				errors.push('Please specify a file.');
			}
			
			var f = new FormData();
			f.append('type', 'climateMaps');
			f.append('file', file);
			$.post({
				url: '/uploadMap',
				data: f,
				success: (data) => {
					data = JSON.parse(data);
					if(data.type == 'error') {
						errors.push('Unable to upload file.');
					}
				},
				contentType: false,
				processData: false,
			});
				
			
			if (errors.length) {
				dlg.querySelector('.error').innerHTML = errors.join('<br>');
				return;
			}
			
			
			let refRow = mapTableMgr.getRow(mapTableMgr.numRows-1);
			let newRow = refRow.cloneNode(true);
			refRow.after(newRow);
			mapTableMgr.setInnerValue(newRow, 'div',
				'id', null,
				'name', mapName,
				'fileName', file.name.replace(/\.[^/.]+$/, ''),
			);
			dismissDialogs();
		}}}),
		n('button', 'Cancel', {on: {click: dismissDialogs}})
	]});
}

function deleteClimateMap() {
	let mapTableMgr = tableManager($('.tabSheet[data-name=climateMaps] .dataTable')[0]);
	popupDialog(n('div',
		'Choose map to delete:', n('ul',
			mapTableMgr.getColumnValues('name').map(v => {
				return n('div',n('label',
					n('input', {type: 'radio', name: 'item', value: v}),
					v,
				))
			})
		),
	), {buttons: [
		n('button', 'Delete', {on: {click: event => {
			let dlg = event.target.closest('.dialog');
			let item = dlg.querySelector('*[name=item]:checked').value;
			
			let refRow = mapTableMgr.findRows({name: item})[0];
			refRow.remove();
			dismissDialogs();
		}}}),
		n('button', 'Cancel', {on: {click: dismissDialogs}})
	]});
}

function addItem() {
	let itemTableMgr = tableManager($('.tabSheet[data-name=items] .dataTable')[0]);
	let $dlg = popupDialog(n('div',
		n('h2', 'Add a new item'),
		n('div.error'),
		n('p', 'Name: ', n('input', {name: 'name'})),
	), {buttons: [
		n('button', 'Add', {on: {click: event => {
			let dlg = event.target.closest('.dialog');
			let itemName = (dlg.querySelector('*[name=name]') || {}).value;
			
			/// Check for errors
			let errors = [];
			if (!itemName) {
				errors.push('Please specify "Name".');
			}
			if (errors.length) {
				dlg.querySelector('.error').innerHTML = errors.join('<br>');
				return;
			}
			
			let refRow = itemTableMgr.getRow(itemTableMgr.numRows-1);
			let newRow = refRow.cloneNode(true);
			newRow.classList.add('new');
			refRow.after(newRow);
			itemTableMgr.setInnerValue(newRow, 'div',
				'name', itemName,
			);
			dismissDialogs();
		}}}),
		n('button', 'Cancel', {on: {click: dismissDialogs}})
	]});
}


function deleteItem() {
	let itemTableMgr = tableManager($('.tabSheet[data-name=items] .dataTable')[0]);
	let pointTableMgr = tableManager($('.tabSheet[data-name=pathwayPoints] .dataTable')[0]);

	popupDialog(n('div',
		'Choose item to delete:',
		n('ul',
			itemTableMgr.getColumnValues('name').slice(1).map(v => {
				return n('div', n('label',
					n('input', { type: 'radio', name: 'item', value: v }),
					v
				))
			})
		)
	), {
		buttons: [
			n('button', 'Delete', {
				on: {
					click: event => {
						let dlg = event.target.closest('.dialog');
						let itemName = dlg.querySelector('*[name=item]:checked').value;

						let refRow = itemTableMgr.findRows({ name: itemName })[0];

						// Try to find the 'id' column index case-insensitively
						let headerRow = refRow.closest('table').querySelector('thead tr');
						let headers = Array.from(headerRow.children).map(th => th.textContent.trim().toLowerCase());

						// console.log("Item table headers:", headers);

						let idIndex = headers.findIndex(h => h === 'id');
						let itemId = refRow.cells[idIndex].textContent.trim();

						// Remove the item row
						refRow.remove();

						// Remove all pathwayPoints with matching itemId
						pointTableMgr.findRows({ itemId }).forEach(row => row.remove());

						dismissDialogs();
					}
				}
			}),
			n('button', 'Cancel', { on: { click: dismissDialogs } })
		]
	});
}





function addPathwayPoint() {
	let pointTableMgr = tableManager($('.tabSheet[data-name=pathwayPoints] .dataTable')[0]);
	let itemValues = tableManager($('.tabSheet[data-name=items] .dataTable')[0]).getColumnValues('name');

	let beforePointContainer = n('ul'); // Empty container for beforePoint options

	let updateBeforePoints = (selectedItem) => {
		beforePointContainer.innerHTML = '';
		const matchingRows = pointTableMgr.findRows({ item: selectedItem });

		if (matchingRows.length === 0) {
			beforePointContainer.appendChild(
				n('div', n('label',
					n('input', { type: 'radio', name: 'beforePoint', value: 'entry' }),
					'Entry point'
				))
			);
		} else {
			matchingRows.forEach(v => {
				let val = v.cells[1].textContent;
				beforePointContainer.appendChild(
					n('div', n('label',
						n('input', { type: 'radio', name: 'beforePoint', value: val }),
						val
					))
				);
			});
		}
	};

	let itemList = n('ul',
		itemValues.map(v => {
			return n('div', n('label',
				n('input', {
					type: 'radio',
					name: 'item',
					value: v,
					on: {
						change: () => updateBeforePoints(v) // FIXED: using `on: {change}`
					}
				}),
				v
			));
		})
	);

	let $dlg = popupDialog(n('div',
		n('h2', 'Add a new pathway point'),
		n('div.error'),
		n('p', 'Name: ', n('input', {name: 'name'})),
		n('div', 'Select associated item:', itemList),
		n('div', 'Add this point after:', beforePointContainer),
		n('div', 'Geometry Type: ', 
			n('label',n('input', {type: 'radio', name: 'geometryType', value: 'point'}),'Point'), 
			n('label',n('input', {type: 'radio', name: 'geometryType', value: 'polygon'}),'Polygon'
		)),
		n('p', 'Choose file: ', n('input', {type: 'file', name: 'filePicker'})),
	), {
		buttons: [
			n('button', 'Add', {
				on: {
					click: event => {
						let dlg = event.target.closest('.dialog');
						let pointName = (dlg.querySelector('*[name=name]') || {}).value;
						let item = (dlg.querySelector('*[name=item]:checked') || {}).value;
						let beforePoint = (dlg.querySelector('*[name=beforePoint]:checked') || {}).value;
						let fileInput = dlg.querySelector('*[name=filePicker]');
						let geometryType = (dlg.querySelector('*[name=geometryType]:checked') || {}).value;
						let file = fileInput?.files[0];

						let errors = [];
						if (!pointName) errors.push('Please specify "Name".');
						if (!item) errors.push('Please specify an item.');
						if (!beforePoint) errors.push('Please specify "Add this point after".');
						if (!geometryType) errors.push('Please specify a geometry type.');
						if (!file) errors.push('Please specify a file.');

						var f = new FormData();
						f.append('type', 'pathway');
						f.append('file', file);
						$.post({
							url: '/uploadMap',
							data: f,
							success: (data) => {
								data = JSON.parse(data);
								if (data.type == 'error') {
									errors.push('Unable to upload file.');
								}
							},
							contentType: false,
							processData: false,
						});

						if (errors.length) {
							dlg.querySelector('.error').innerHTML = errors.join('<br>');
							return;
						}
						
						let refRow = beforePoint === 'start'
							? null
							: pointTableMgr.findRows({ name: beforePoint })[0];

						let newRow = (refRow || pointTableMgr.table.tBodies[0].rows[0]).cloneNode(true);
						newRow.classList.add('new');

						// Insert after refRow, or at end if refRow is null
						if (refRow) {
							refRow.after(newRow);
						} else {
							pointTableMgr.table.tBodies[0].appendChild(newRow);
						}

						pointTableMgr.setInnerValue(newRow, 'div',
							'name', pointName,
							'item', item,
							'tableName', file.name.replace(/\.[^/.]+$/, ''),
							'shape', geometryType,
							'timeAtSite', 'Normal(2,1)',
						);

						dismissDialogs();
					}
				}
			}),
			n('button', 'Cancel', {on: {click: dismissDialogs}})
		]
	});
}


function deletePathwayPoint() {
	let pointTableMgr = tableManager($('.tabSheet[data-name=pathwayPoints] .dataTable')[0]);
	let rows = pointTableMgr.getTableValues().data;

	popupDialog(n('div',
		'Choose point to delete:',
		n('ul',
			rows.map(row => {
				const [id, name, item] = row;
				let label = `${item}: ${name}`;
				return n('div', n('label',
					n('input', {type: 'radio', name: 'point', value: id}),
					label
				));
			})
		)
	), {
		buttons: [
			n('button', 'Delete', {
				on: {
					click: event => {
						let dlg = event.target.closest('.dialog');
						let point = dlg.querySelector('*[name=point]:checked').value;

						let refRow = pointTableMgr.findRows({id: point})[0];
						refRow.remove();
						dismissDialogs();
					}
				}
			}),
			n('button', 'Cancel', {on: {click: dismissDialogs}})
		]
	});
}


function addViewLinks() {
	let mapTableMgr = tableManager($('.tabSheet[data-name=climateMaps] .dataTable')[0])
	mapTableMgr.getColumnCells('fileName').forEach(td => {
		let id = mapTableMgr.getValue(td, 'id');
		td.querySelector('div').append(
			n('span.exclude',
				' (',
				n('a', {target: '_blank', href: '/viewParameterData?table=climateMap&id='+id}, 'View'),
				')',
			)
		);
	});
	
	let pointTableMgr = tableManager($('.tabSheet[data-name=pathwayPoints] .dataTable')[0])
	pointTableMgr.getColumnCells('tableName').forEach(td => {
		let id = pointTableMgr.getValue(td, 'id');
		td.querySelector('div').append(
			n('span.exclude',
				' (',
				n('a', {target: '_blank', href: '/viewParameterData?table=pathwayPoint&id='+id}, 'View'),
				')',
			)
		);
	});
	
}


var ui = {
	message(msg) {
		ui.dialog(msg, {
			buttons: [$('<button>').text('OK').on('click', ui.dismissDialogs)]
		});
	},
	
	dialog(...args) { popupDialog(...args) },
	
	dismissDialogs(...args) { dismissDialogs(...args) }
};



function getCurrentParameters() {
	let stage = $('[name=displayValue]:checked').val();
	let month = $('.month').length ? $('.month').val() : null;
	let location = $('input.location').val();
	let locationCode = null;
	if (location) {
		locationCode = $('#places').find(`option[value="${location.replace(/"/g, '\\"')}"]`).data('value');
	}
	
	return {stage, month, locationCode};
}


function colorPoly(val) {
	if (mapDiff) {
		// Diff mode: blue = negative, white = 0, red = positive
		const maxAbs = Math.max(Math.abs(minVal), Math.abs(maxVal));
		const magnitude = Math.min(1, Math.abs(val) / maxAbs);

		let r, g, b;
		if (val > 0) {
			// White → Red
			r = 255;
			g = Math.round(255 * (1 - magnitude));
			b = Math.round(255 * (1 - magnitude));
		} else if (val < 0) {
			// White → Blue
			r = Math.round(255 * (1 - magnitude));
			g = Math.round(255 * (1 - magnitude));
			b = 255;
		} else {
			// Zero = white
			r = g = b = 255;
		}
		return `rgb(${r},${g},${b})`;
	} else {
		// Standard mode: white to red gradient
		let valAsFraction = (val - minVal) / (maxVal - minVal);
		valAsFraction = Math.max(0, Math.min(1, valAsFraction)); // Clamp between 0 and 1

		let startColor = [255, 255, 255]; // White
		let endColor = [255, 0, 0];       // Red

		let r = Math.round(startColor[0] + valAsFraction * (endColor[0] - startColor[0]));
		let g = Math.round(startColor[1] + valAsFraction * (endColor[1] - startColor[1]));
		let b = Math.round(startColor[2] + valAsFraction * (endColor[2] - startColor[2]));

		return `rgb(${r},${g},${b})`;
	}
}


function colorPolys() {
	$('.nzMap polygon[data-code]').css('fill', 'white');
	const polys = document.querySelectorAll('.nzMap polygon[data-code]');
	for (let i = 0; i < polys.length; i++) {
		const code = polys[i].getAttribute('data-code');
		let val = null;

		if (mapDiff) {
			const current = mapData[code]?.uPeSqKm ?? 0;
			const base = baseMapData[code]?.uPeSqKm ?? 0;
			val = current - base;
		} else {
			val = mapData[code]?.uPeSqKm ?? null;
		}

		polys[i].style.fill = val != null ? colorPoly(val) : 'white';
	}
}

function createLegend(o) {
	o = o || {};
	o.ranked = o.ranked || false;
	o.colorScale = o.colorScale || 1;
	o.scaleMin = typeof o.scaleMin === "undefined" ? null : o.scaleMin;
	o.scaleMax = typeof o.scaleMax === "undefined" ? null : o.scaleMax;
	o.scaleType = typeof o.scaleType === "undefined" ? (mapDiff ? 'diff' : 'abs') : o.scaleType;

	// Remove any existing scale
	$('.mapPanel .scale').remove();
	$('.mapPanel .diffScale').remove();

	const $scale = $('<div class=' + (o.scaleType === 'abs' ? 'scale' : 'diffScale') + '>').appendTo('.mapPanel');

	const scaleHeight = 200;
	const numMarks = 5;

	let scaleMin = o.scaleMin !== null ? o.scaleMin : Math.min(...values);
	let scaleMax = o.scaleMax !== null ? o.scaleMax : Math.max(...values);
	let marks = [];

	if (o.scaleType === 'diff') {
		// Diverging legend from min (blue) → 0 (white) → max (red)
		const maxAbs = Math.max(Math.abs(scaleMin), Math.abs(scaleMax));
		marks = [-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs];
	} else {
		// Absolute legend from min (white) → max (red)
		const interval = (scaleMax - scaleMin) / (numMarks - 1);
		for (let i = 0; i < numMarks; i++) {
			marks.push(scaleMin + interval * i);
		}
	}

	// Draw each mark
	for (let i = 0; i < marks.length; i++) {
		const mark = marks[marks.length - 1 - i]; // Top-down
		$scale.append(
			$('<div class="scaleMark">')
				.css({ top: (scaleHeight / (numMarks - 1)) * i - 7 })
				.text(sigFig(mark, 3))
		);
	}
}



async function updateMap() {
	let params = getCurrentParameters();
	
	stage = params.stage;
	month = params.month;

	const result = await $.getJSON('/getMapData', { scenarioId, stage, month });
	mapData = result['mapData']
	baseMapData = result['baseMapData']

	if(mapDiff){
		values = Object.keys(mapData).map(code => {
				const current = mapData[code]?.uPeSqKm ?? 0;
				const base = baseMapData[code]?.uPeSqKm ?? 0;
				return current - base;
			});
	}
	else {
		values = Object.values(mapData).map(entry => entry.uPeSqKm);
	}

	minVal = Math.min(...values);
	maxVal = Math.max(...values);
	
	colorPolys();
	createLegend({
		scaleMin: minVal,
		scaleMax: maxVal,
		scaleType: mapDiff ? 'diff' : 'abs'
	});
}



function makeTimeline() {
	let monthsShort = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(/ /);
	let labels =  new Array(numMonths).fill(0).map((m, i) => `${monthsShort[i%monthsShort.length]} (Y${Math.floor(i/monthsShort.length)})`);
	
	$current = $('.pointGraph').append($('<canvas width=300 height=200>'));

	var ctx = $current.find('canvas')[0].getContext('2d');
	timelineChart = new Chart(ctx, {
		type: 'line',
		data: {
			labels: labels,
			datasets: [{
				data: timeData,
				backgroundColor: 'rgba(255, 99, 132, 0.4)',
				borderColor: 'rgba(255,99,132,1)',
			},{
				data: baseTimeData,
				backgroundColor: 'rgba(132, 99, 255, 0.4)',
				borderColor: 'rgba(132,99,255,1)',
				hidden: true,
			}]
		},
		options: {
			onClick: function(event, points) {
				let currentParams = getCurrentParameters();
				window.location.href = changeQsUrl(window.location.href, {...currentParams, type: 'map', month: points[0]._index});
			},
			hover: {
				intersect: false,
			},
			
			tooltips: {
				mode: 'index',
				intersect: false,
			},
			legend: false,
			maintainAspectRatio: false,
			scales: {
				yAxes: [{
					ticks: {
						beginAtZero:true
					}
				}]
			}
		}
	});			
}

async function updateTimeData() {
	let params = getCurrentParameters();
	//console.log(params)
	
	stage = params.stage;
	locationCode = params.locationCode;
	
	timeData = await new Promise(res => $.getJSON('/getTimeData', {scenarioId,stage,locationCode}).then(res));
	
	timelineChart.data.datasets[0].data = timeData
	timelineChart.update();
}







///project page

function saveSettings(form) {
	ui.dialog(`<h2>Save Settings</h2>
		<p>Changing setting will invalidate previous runs, are you sure you want to continue?`, {
		buttons: [
			$('<button>').text('Continue').on('click', function() {
				$.get("/resetProject", {projectId}, function(data) {
					updateScenarioList()
					$.post("/saveSettings", $(form).serialize()).always(function(ret) {});
				});
				ui.dismissDialogs();
			}),
			$('<button>').text('Cancel').on('click', ui.dismissDialogs),
		],
	});
}

function deleteScenario(scenarioId) {
	ui.dialog(`<h2>Delete Scenario</h2>
		<p>Are you sure you wish to delete this scenario?`, {
		buttons: [
			$('<button>').text('Delete Scenario').on('click', function() {
				$.post('/deleteScenario', {scenarioId}, function(data) {
					if (data == "OK") {
						window.location.href = '/project?id='+projectId
					}
					else if (data == "DeleteProject") {
						window.location.href = '/'
					}
					else {
						ui.message(`Delete failed<pre>${toHtml(data)}</pre>`);
					}
				});
				ui.dismissDialogs();
			}),
			$('<button>').text('Cancel').on('click', ui.dismissDialogs),
		],
	});
}

function runScenario(scenarioId) {
	$.post('/runScenario', {scenarioId}, function(data) {
		window.location.href = '/project?id='+projectId
	});
}

function runProject() {
	$.post('/runProject', {projectId}, function(data) {
		window.location.href = '/project?id='+projectId
	});
}

function scenarioTable(scenarioId) {
	window.location.href = '/scenario?id='+scenarioId
}

function makeBase(scenarioId) {
	$.post('/saveBaseScenario', {scenarioId}, function(data) {
		if (data == "OK") {
			updateScenarioList()
			// ui.message(`updated base scenario`);
			// window.location.href = '/scenario?id='+scenarioId;
		}
		else {
			ui.message(`Could not save base scenario<pre>${toHtml(data)}</pre>`);
		}
	});
}

function cancelRun(scenarioId) {
	ui.dialog(`<h2>Cancel Run</h2>
	
		<p>Are you sure you wish to cancel this run?`, {
		buttons: [
			$('<button>').text('Yes').on('click', function() {
				$.post('/killScenario', {scenarioId}, function(data) {
					window.location.href = '/project?id='+projectId
				});
				ui.dismissDialogs();
			}),
			$('<button>').text('No').on('click', ui.dismissDialogs),
		],
	});
}

function addScenario() {
	ui.dialog(`<h2>Add Scenario</h2>
	
		<p>Would you like to upload or copy the base scenario?`, {
		buttons: [
			$('<button>').text('Upload').on('click', function() {
				$('input.addScenarioFile').val('');
				$('input.addScenarioFile').click();
				ui.dismissDialogs();
			}),
			$('<button>').text('Copy').on('click', function() {
				$.post('/copyBaseScenario', {baseScenarioId}, (scenarioId) => {
					window.location.href = '/scenario?editName=1&id='+scenarioId;
				});
				ui.dismissDialogs();
			}),
			$('<button>').text('Cancel').on('click', ui.dismissDialogs),
		],
	});
}

$(document).on('change', 'input.addScenarioFile', function() {
	console.log('here')
	var f = new FormData();
	f.append('sheet', this.files[0], this.files[0].name);
	f.append('projectId', projectId);
	$.ajax({
		url: '/uploadScenario',
		type: 'POST',
		data: f,
		success: (data) => {
			data = JSON.parse(data);
			if(data.type == 'error') {
				dismissDialogs();
				ui.message(data.message);
			}
			else {
				window.location.href = '/scenario?editName=1&id=' + data;
			}
		},
		contentType: false,
		processData: false,
	});
});

async function updateScenarioList() {
	const response = await fetch(`/scenarioList?projectId=${projectId}`);
	const scenarioHtml = await response.text();
	document.querySelector('.scenarioList').innerHTML = scenarioHtml;
}