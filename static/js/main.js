
// To prevent page change after rating
document.addEventListener("submit", function (e) {
    if (!e.target.classList.contains("rating-form")) return;

    e.preventDefault(); // prevent reload

    const formData = new FormData(e.target);

    fetch("/rate_movie", {
        method: "POST",
        body: formData
    })
    .then(async res => {
        if (res.status === 401) {
            window.location.href = "/login";
            return;
        }
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
    })
    .then(data => {
        if (!data) return;
        console.log(data);
    })
    .catch(err => console.error("Fetch error:", err));
});
