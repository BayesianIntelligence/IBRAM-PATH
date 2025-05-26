$(document).ready(function() {
	$(document).on('click', '.tabButtons button', function(e) {
		var tabSet = $(this).closest('.tabSet');
		var tabSheetToActivate = tabSet.find('.tabSheet[data-name='+$(this).data('for')+']');

		/// Set the active tab sheet
		tabSet.find('.tabSheet').hide(0, function() { $(this).removeClass('active'); });
		tabSheetToActivate.show(0, function() { $(this).addClass('active'); });

		/// Set the selected button
		tabSet.find('.tabButtons .selected').removeClass('selected');
		$(this).addClass('selected');
	});
});

