var map;
var infowindow;
var map_markers = {};
var dest;
var alternates = [];

// Initialize and add the map
function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 3.7,
        center: { lat: 39.49202, lng: -97.94105 },
    });
    infowindow = new google.maps.InfoWindow();
}

// Move map center to new coordinates
function updateMap(lat, lng) {
    const center = new google.maps.LatLng(Number(lat), Number(lng));
    map.panTo(center);
    map.setZoom(8);
}

// Add a new map marker with the information of an airport
function addmarker(airport, col) {
    var infoString;
    if (dest != undefined && airport.icao == dest.icao) {
        infoString = "Destination" + "<br>";
        infoString += "Icao: " + airport.icao;
    } else {
        infoString = "Icao: " + airport.icao + "<br>";
        infoString += "Distance: " + airport.distance + "km <br>";
        infoString += "Has tower: " + airport.has_tower + "<br>";
        infoString += "Longest Runway: " + airport.longest_runway + " ft <br>";
        infoString += "Approaches: " + airport.approaches;
    }

    center = new google.maps.LatLng(Number(airport.lat), Number(airport.lon));
    let url = "http://maps.google.com/mapfiles/ms/icons/" + col + "-dot.png";
    marker = new google.maps.Marker({
        position: center,
        map: map,
        icon: {
            url: url,
        }
    });

    google.maps.event.addListener(marker, 'click', (function (marker) {
        return function () {
            infowindow.setContent(infoString);
            infowindow.open(map, marker);
        }
    })(marker));
    map_markers[airport.icao] = marker;
}

// Remove all markers on te map
function removeMarkers() {
    icaos = Object.keys(map_markers)
    for (i = 0; i < icaos.length; i++) {
        map_markers[icaos[i]].setMap(null)
        delete map_markers[icaos[i]]
    }
}

// Perform an http request
function httpRequest(url, method, body = "") {
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open(method, url, false); // false for synchronous request
    xmlHttp.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xmlHttp.send(JSON.stringify(body));
    return xmlHttp.responseText;
}

// Find and present alternates based on typed destination airport and aircraft model
function submitform() {
    var destination_icao = document.getElementById("dest_form").value;
    var aircraft_icao = document.getElementById("aircraft_form").value;
    url = "http://localhost:5005/lookupsICAO?dest=" + destination_icao + "&aircraft=" + aircraft_icao;
    res = httpRequest(url, "GET")
    res_json = JSON.parse(res.replace(/\bNaN\b/g, "null"))
    dest = res_json.dest;
    alternates = res_json.alternates
    console.log(res_json)

    removeMarkers();
    addmarker(dest, "green");
    updateMap(dest.lat, dest.lon);

    document.getElementById("alternate_input").value = "";

    // Populating drop down list
    document.getElementById("radioForm").innerHTML = '';
    var options = "";
    for (var i = 0; i < alternates.length; i++) {
        if (i >= 10) {
            break;
        }

        createRadioButtons(alternates[i], false);
        addmarker(alternates[i], "red");
    }
    document.getElementById('alternate_list').innerHTML = options;
}


function manualAlternateSelected() {
    inputted_icao = document.getElementById('alternate_input').value
    var airport = requestAirportInfo(inputted_icao);
    airport.distance = 7153.89;    
    addmarker(airport, "red");
    google.maps.event.trigger(map_markers[airport.icao], "click");
}


function requestAirportInfo(icao) {
    url = "http://localhost:5005/getairportinfo?icao=" + icao;
    res = httpRequest(url, "GET")
    airport_json = JSON.parse(res.replace(/\bNaN\b/g, "null"))
    return airport_json
}


function createRadioButtons(alternate, checked) {
    var radioform = document.getElementById('radioForm')

    var input = document.createElement('input');
    input.type = 'radio';
    input.name = "buttonGroup";
    input.value = alternate.icao;
    input.checked = false;
    var label = document.createElement('label');
    label.textContent = alternate.icao;
    var lineBreak = document.createElement("br")

    radioform.appendChild(input);
    radioform.appendChild(label);
    radioform.appendChild(lineBreak);
}


window.onload = function () {
    var radioform = document.getElementById("radioForm");
    radioform.addEventListener("click", function () {
        for (var i = 0; i < radioform.length; i++) {
            if (radioform[i].type = "radio") {
                if (radioform[i].checked) {
                    var selectedIcao = radioform[i].value;
                    let marker = map_markers[selectedIcao];
                    google.maps.event.trigger(marker, "click");
                }
            }
        }
    });
}
