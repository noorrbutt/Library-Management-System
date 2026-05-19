document.addEventListener("DOMContentLoaded", () => {
  // ── Element refs ──────────────────────────────────────────────────────────
  const editBtn        = document.getElementById("edit-btn");
  const toggleBtn      = document.getElementById("toggle-btn");
  const cancelBtn      = document.getElementById("cancel-btn");
  const saveBtn        = document.getElementById("save-btn");
  const deleteBtn      = document.getElementById("delete-btn");

  const checkCols      = document.querySelectorAll(".checkbox-col");
  const selectAll      = document.getElementById("select-all");
  const deleteForm     = document.getElementById("book-form");
  const editForm       = document.getElementById("edit-form");
  const booksDataInput = document.getElementById("books-data");
  const confirmDeleteBtn   = document.getElementById("confirmDeleteBtn");
  const confirmDeleteModal = new bootstrap.Modal(document.getElementById("confirmDeleteModal"));

  const actionToast  = document.getElementById("actionToast");
  const toastMessage = document.getElementById("toastMessage");
  const bsToast      = actionToast ? new bootstrap.Toast(actionToast, { delay: 3000 }) : null;

  let selecting = false;
  let editing   = false;

  // ── Toast ─────────────────────────────────────────────────────────────────
  function showToast(message, type = "success") {
    if (!bsToast) return;
    actionToast.classList.remove("bg-success", "bg-danger");
    actionToast.classList.add(type === "success" ? "bg-success" : "bg-danger");
    toastMessage.textContent = message;
    bsToast.show();
  }

  // ── Show / hide context buttons ───────────────────────────────────────────
  function showContextButtons(mode) {
    // mode: "edit", "select", or null (reset)
    saveBtn.classList.toggle("d-none",   mode !== "edit");
    deleteBtn.classList.toggle("d-none", mode !== "select");
    cancelBtn.classList.toggle("d-none", mode === null);
  }

  // ── EDIT mode ─────────────────────────────────────────────────────────────
  editBtn.addEventListener("click", () => {
    if (selecting) return;           // ignore if select mode is on
    editing = true;
    showContextButtons("edit");

    document.querySelectorAll(".editable").forEach(cell => {
      const value = cell.textContent.trim();
      cell.innerHTML = `<input type="text" class="form-control form-control-sm" value="${value}">`;
    });
  });

  // ── SAVE button ───────────────────────────────────────────────────────────
  saveBtn.addEventListener("click", () => {
    const rows = document.querySelectorAll("tbody tr");
    const booksData = [];
    rows.forEach(row => {
      const fields = row.querySelectorAll(".editable input");
      booksData.push({
        id:       row.getAttribute("data-id"),
        name:     fields[0].value,
        quantity: fields[1].value,
        author:   fields[2].value,
        category: fields[3].value,
        language: fields[4].value,
      });
    });
    booksDataInput.value = JSON.stringify(booksData);
    showToast("Book(s) updated successfully");
    editForm.submit();
  });

  // ── SELECT mode ───────────────────────────────────────────────────────────
  toggleBtn.addEventListener("click", () => {
    if (editing) return;             // ignore if edit mode is on
    selecting = true;
    showContextButtons("select");
    checkCols.forEach(col => col.classList.remove("hidden-checkbox"));
  });

  // ── DELETE button (triggers modal) ───────────────────────────────────────
  deleteBtn.addEventListener("click", () => {
    const anyChecked = document.querySelectorAll('input[name="selected_books"]:checked').length > 0;
    if (!anyChecked) {
      showToast("Select at least one book first.", "error");
      return;
    }
    confirmDeleteModal.show();
  });

  confirmDeleteBtn.addEventListener("click", () => {
    showToast("Book(s) deleted successfully");
    deleteForm.submit();
  });

  // ── SELECT ALL ────────────────────────────────────────────────────────────
  selectAll?.addEventListener("change", function () {
    document.querySelectorAll('input[name="selected_books"]')
      .forEach(cb => cb.checked = this.checked);
  });

  // ── CANCEL ────────────────────────────────────────────────────────────────
  cancelBtn.addEventListener("click", () => {
    if (editing) {
      editing = false;
      // Restore cell text from the input's current value
      document.querySelectorAll(".editable").forEach(cell => {
        const input = cell.querySelector("input");
        if (input) cell.textContent = input.getAttribute("value"); // original value
      });
    }
    if (selecting) {
      selecting = false;
      checkCols.forEach(col => col.classList.add("hidden-checkbox"));
      document.querySelectorAll('input[name="selected_books"]')
        .forEach(cb => cb.checked = false);
      selectAll && (selectAll.checked = false);
    }
    showContextButtons(null); // hide all context buttons
  });

  // ── Filter toggle (inline in template, but guard if it exists here too) ──
  document.getElementById("filterToggleBtn")?.addEventListener("click", function () {
    const fc = document.getElementById("filterCollapse");
    if (fc) fc.style.display = fc.style.display === "none" ? "block" : "none";
  });
});