// Small progressive-enhancement touches. The app works with JS disabled.
document.addEventListener("DOMContentLoaded", () => {
  const file = document.querySelector("#file");
  const name = document.querySelector("#filename");
  if (file && name) {
    file.addEventListener("change", () => {
      if (file.files && file.files[0]) name.value = file.files[0].name;
    });
  }

  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("button[type=submit]");
      if (button) {
        button.disabled = true;
        button.textContent = "Working...";
      }
    });
  });

  const toast = document.querySelector(".toast");
  if (toast) {
    window.setTimeout(() => toast.remove(), 4000);
  }
});
