



(function () {
  const modalElement = document.getElementById("confirm-modal");
  const modal = new bootstrap.Modal(modalElement);
  const message = document.getElementById("confirm-message");
  const okButton = document.getElementById("confirm-ok");
  let onConfirm = null;

  function ask(question, action) {
    message.textContent = question;
    onConfirm = action;
    modal.show();
  }

  okButton.addEventListener("click", () => {
    modal.hide();
    if (onConfirm) onConfirm();
    onConfirm = null;
  });

  document.addEventListener("htmx:confirm", (event) => {
    if (!event.detail.question) return;
    event.preventDefault();
    ask(event.detail.question, () => event.detail.issueRequest(true));
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!form.dataset.confirm || form.dataset.confirmed) return;
    event.preventDefault();
    ask(form.dataset.confirm, () => {
      form.dataset.confirmed = "yes";
      form.requestSubmit();
    });
  });
})();
