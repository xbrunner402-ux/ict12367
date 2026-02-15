const fullImg = document.querySelector(".full-image");
const smallImg = document.querySelectorAll(".gallery img");
const modal = document.querySelector(".modal");

smallImg.forEach(img => {
    img.addEventListener("click", () => {
        modal.classList.add("open");
        const imgNum = img.getAttribute("alt");
        fullImg.src = `foods-images/${imgNum}.jpg`; 
    });
});

modal.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
        modal.classList.remove("open");
    }
});