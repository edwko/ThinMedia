async function fetchText(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch data. Status: ${response.status}`);
    }
    return await response.text();
  } catch (error) {
    console.error("Error fetching data:", error.message);
  }
}

function load_media() {
  const url = "/home-media-html";
  fetchText(url).then((data) => {
    var media_div = document.getElementById("media");
    media_div.innerHTML = data;
  });
}

function load_unique_genres() {
  const url = "/unique-genres-html";
  fetchText(url).then((data) => {
    var media_div = document.getElementById("unique_genres");
    media_div.innerHTML = data;
  });
}

function media_type(input) {
  const url = "/set-media-type?type=";
  fetchText(url + input).then((data) => {
    load_media();
    load_unique_genres();
  });
}

function set_media_filter(input) {
  const url = "/set-media-filter?filter=";
  fetchText(url + input).then((data) => {
    load_media();
    load_unique_genres();
  });
}

function media_search(input) {
  var search = input.value;
  const url = "/home-media-html?search=";
  fetchText(url + search).then((data) => {
    var media_div = document.getElementById("media");
    media_div.innerHTML = data;
  });
}

function clear_all_selected_genres() {
  const url = "/clear-all-genres";
  fetchText(url).then((data) => {
    load_media();
    load_unique_genres();
  });
}

window.addEventListener("load", load_media);
window.addEventListener("load", load_unique_genres);
