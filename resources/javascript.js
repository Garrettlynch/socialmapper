
/* Retrieve URL variable */

function getSearchParameters()
{
	var prmstr = window.location.search.substr(1);
	return prmstr != null && prmstr != "" ? transformToAssocArray(prmstr) : {};
}


function transformToAssocArray(prmstr)
{
	var params = {};
	var prmarr = prmstr.split("&");

	for ( var i = 0; i < prmarr.length; i++)
	{
		var tmparr = prmarr[i].split("=");
		params[tmparr[0]] = tmparr[1];
	}

	return params;
}

/* Retrieve URL variable */



/* Show/hide admin login */

function toggleAdminModal()
{
	const modal = document.getElementById('admin-modal');
	const content = modal.querySelector('.modal-content');

	const password = modal.querySelector('input[name="password"]');

	const isVisible = modal.style.display === 'block';

	const errorSpan = modal.querySelector('.error');
	const messageSpan = modal.querySelector('.message');
	errorSpan.style.display = "none";
	messageSpan.style.display = "none";
	errorSpan.innerText = "";
	messageSpan.innerText = "";

	if (isVisible)
	{
		// animate out
		content.classList.add('hide');
		content.addEventListener('animationend', function handleClose() {
			modal.style.display = 'none';
			content.classList.remove('hide');
			content.removeEventListener('animationend', handleClose);
		}, { once: true });

	} else {
		// animate in
		modal.style.display = 'block';
		content.classList.remove('hide'); // Clear state for entrance animation

		// delay to ensure modal is rendered before focusing
		setTimeout(() => password.focus(), 500);
	}
}

/* Show/hide admin login */



/* Logout button */

function addLogoutControl()
{
	const LogoutControl = L.Control.extend({
		options: {
			position: 'topright' // Places it near the layer toggle
		},

		onAdd: function(map) {
			const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
			const button = L.DomUtil.create('a', '', container);

			button.innerHTML = 'Logout';
			button.href = '#';
			button.classList.add('logout');

			L.DomEvent.on(button, 'click', function(e) {
				L.DomEvent.stopPropagation(e);
				L.DomEvent.preventDefault(e);

				localStorage.removeItem('map_admin_auth');
				window.location.href = window.location.origin + window.location.pathname;

			});

			return container;
		}
	});

	map.addControl(new LogoutControl());
}

/* Logout button */



/* Alert */

function showAlert(message)
{
	document.getElementById('alert-message').innerText = message;
	document.getElementById('alert-modal').style.display = 'block';
}

/* Alert */




(function() {

	/* SHA-256 has a string */

	async function hashPassword(string)
	{
		const utf8 = new TextEncoder().encode(string);
		const hashBuffer = await crypto.subtle.digest('SHA-256', utf8);
		const hashArray = Array.from(new Uint8Array(hashBuffer));
		return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
	}

	/* SHA-256 has a string */



	let layerControl = null;

	function initAdminTools()
	{
		// prevents adding multiple controls if they login twice
		if (layerControl) return;

		const overlayMaps = {
			"Show Coordinates": debugGrid
		};

		// add the control to the map
		layerControl = L.control.layers(null, overlayMaps, { collapsed: false }).addTo(map);

		// add the logout button
		addLogoutControl();

		// automatically turn on the grid once logged in
		debugGrid.addTo(map);
	}



	// when dom is loaded
	document.addEventListener('DOMContentLoaded', function() {

		// check for existing session
		const isAuthenticated = localStorage.getItem('map_admin_auth') === 'true';

		if (isAuthenticated) initAdminTools();

		// handle URL Parameter for Modal
		const params = getSearchParameters();
		if (params.admin == "login")
		{
			if (!isAuthenticated) toggleAdminModal();
		}

		const submitBtn = document.getElementById('login-button');

		// only attach if the button actually exists on the page
		if (submitBtn)
		{
			submitBtn.addEventListener('click', async function(e) {
				e.preventDefault(); // Prevents the form from refreshing the page

				const passwordInput = document.querySelector('input[name="password"]').value;
				const errorSpan = document.querySelector('.error');

				// Replace with your generated SHA-256 hash
				// Example: The hash for "mapadmin2026"
				const correctHash = "8ba526311bd36f0eb139dc5b8594482fc69cbec1162d3301aff04483c53f2286";
				const enteredHash = await hashPassword(passwordInput);

				if (enteredHash === correctHash)
				{
					toggleAdminModal();
					initAdminTools();
					localStorage.setItem('map_admin_auth', 'true');
				} else {
					errorSpan.innerText = "Invalid credentials";
					errorSpan.style.display = "block";
				}
			});
		}

		// keyboard Shortcut (Enter key)
		const passField = document.querySelector('input[name="password"]');

		if (passField)
		{
			passField.addEventListener('keypress', function (e) {
				if (e.key === 'Enter') submitBtn.click();
			});
		}

	});

})();






