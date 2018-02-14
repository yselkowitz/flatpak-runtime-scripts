function formatChild(data) {
    if (data.extra_packages && data.extra_packages.length) {
	extra_packages = '<h2>Extra Packages</h2>' +
	    '<span class="package">' + data.extra_packages.join('</span>, <span class="package">') + '</span>';
    } else {
	extra_packages = ''
    }
    return '' +
	'<table class="stars">' +
	'<thead><tr><th>0</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th></tr></thead>' +
	'<tbody><tr><td>' + data.stars[0] + '</td><td>' + data.stars[1] + '</td><td>' + data.stars[2] + '</td><td>' + data.stars[3] + '</td><td>' + data.stars[4] + '</td><td>' + data.stars[5] + '</td></tr><tbody>' +
	'</table>' +
	'<div class="description">' + data.description + '<div>' +
	extra_packages
}

function startAppReport() {
    table = $('#appTable').DataTable( {
	ajax: {
	    url: 'applications.json',
	    cache: true,
	    dataSrc: 'applications',
	},
	createdRow: function(row, data) {
            if (data.package == null && data.flathub != null)
		$(row).addClass('no-fedora')
            if (data.package != null && data.flathub == null)
		$(row).addClass('no-flathub')
            if (data.flathub == null && data.package == null)
		$(row).addClass('no-flathub-fedora')
	},
	columns: [
	    { data: 'name', className: 'text-left' },
	    { data: 'package', defaultContent: '', className: 'text-left' },
	    { data: 'flathub', defaultContent: '', render: {
		display: function(data) { return data != null ? 'true' : '' },
		sort: function(data) { return data != null ? 0 : 1 },
       	    },
	      className: 'text-center' },
	    { data: 'star_total', defaultContent: '', className: 'text-center' },
	    { data: 'star_avg', defaultContent: '', render: {
		display: function(data, type, row, meta) { return data ? data.toFixed(1) : '' }
	    }, className: 'text-center' },
	    { data: 'extra_packages', defaultContent: '', render: {
		display: function(data, type, row, meta) { return data ? data.length: '' },
		sort: function(data, type, row, meta) { return data ? data.length : 0 },
	    }, className: 'text-center' },
	],
	order: [[3, 'desc']],
	pageLength: 100,
	lengthMenu: [[25,100,250,-1],['25', '100', '250', 'All']],
    })
    $('#appTable').on('click', 'td', function () {
        var tr = $(this).closest('tr');
        var row = table.row( tr );

        if ( row.child.isShown() ) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('shown');
        }
        else {
            // Open this row
            row.child( formatChild(row.data()) ).show();
            tr.addClass('shown');
        }
    } );
}

function fillDetails(pkg, category, apps) {
    $('#details .pkg').text(pkg);
    $('#details .category').text(category);
    $('#details .apps').empty();

    for (let a of apps) {
	$('<li></li>').text(a).appendTo('#details .apps');
    }
}

function startPackageTable(id, src) {
    var table = $(id).DataTable( {
	ajax: {
	    url: 'application-packages.json',
	    cache: true,
	    dataSrc: src,
	},
	columns: [
	    { data: 'package', className: 'text-left' },
	    { data: 'top_count', defaultContent: '', className: 'text-center top' },
	    { data: 'all_count', defaultContent: '', className: 'text-center all' },
	],
	order: [[2, 'desc']],
	pageLength: 25,
    });

    $(id).on('click', 'td.top', function () {
        var tr = $(this).closest('tr');
        var row = table.row( tr );

	data = row.data()
	fillDetails(data['package'], 'Top 100', data['top'])
    } );

    $(id).on('click', 'td.all', function () {
        var tr = $(this).closest('tr');
        var row = table.row( tr );

	data = row.data()
	fillDetails(data['package'], ' All', data['all'])
    } );
}

function startAppPackages() {
    startPackageTable('#runtimeTable', 'runtime')
    startPackageTable('#extraTable', 'extra')
}

function closeSummary() {
    $('.summary').hide();
}
