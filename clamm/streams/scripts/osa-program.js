(function () {
	var playlistName = 'temp-playlist';
	var app = Application('iTunes');
	var search_term = "Andrew Manze  Academy of Ancient Music Bach Solo  Double Violin Concertos"
	var library = app.libraryPlaylists[0];
	var result;
	var list;

	app.run();

	result = app.search(library, {
		for: search_term,
		only: 'all'
	});

	try {
		app.userPlaylists[playlistName]();
	} catch (e) {
		console.log('create playlist');
		app.make({
			new: 'playlist',
			withProperties: {
				name: playlistName
			}
		});
	}

	list = app.userPlaylists[playlistName];

	app.delete(list.tracks);

	result.forEach(function (element) {
		app.duplicate(element, {
			to: list
		});
	});

	console.log(list.time());

	return [
		playlistName,
		result.length
	];
})();
