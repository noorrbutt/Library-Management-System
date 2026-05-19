document.addEventListener("DOMContentLoaded", () => {
  // ── Element refs ──────────────────────────────────────────────────────────
  const editBtn           = document.getElementById("edit-btn");
  const toggleBtn         = document.getElementById("toggle-btn");
  const cancelBtn         = document.getElementById("cancel-btn");
  const saveBtn           = document.getElementById("save-btn");
  const deleteBtn         = document.getElementById("delete-btn");
  const filterBtn         = document.getElementById("filter-btn");
  const filterCollapse    = document.getElementById("filterCollapse");

  const table             = document.getElementById("studentsTable");
  const deleteForm        = document.getElementById("student-form");
  const editForm          = document.getElementById("edit-form");
  const studentsDataInput = document.getElementById("students-data");
  const confirmDeleteBtn  = document.getElementById("confirmDeleteBtn");
  const confirmDeleteModal = new bootstrap.Modal(document.getElementById("confirmDeleteModal"));

  const actionToast  = document.getElementById("actionToast");
  const toastMessage = document.getElementById("toastMessage");
  const bsToast      = actionToast ? new bootstrap.Toast(actionToast, { delay: 3000 }) : null;

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
    saveBtn.classList.toggle("d-none",   mode !== "edit");
    deleteBtn.classList.toggle("d-none", mode !== "select");
    cancelBtn.classList.toggle("d-none", mode === null);
  }

  // ── Filter toggle ─────────────────────────────────────────────────────────
  filterBtn?.addEventListener("click", () => {
    const isOpen = filterCollapse.style.display === "block";
    filterCollapse.style.display = isOpen ? "none" : "block";
    filterBtn.innerHTML = isOpen
      ? '<i class="fas fa-filter"></i> Filter'
      : '<i class="fas fa-times"></i> Close Filter';
  });

  // ── Search: skip empty q ──────────────────────────────────────────────────
  const searchForm  = document.getElementById("search-form");
  const searchInput = searchForm?.querySelector('input[name="q"]');
  if (searchInput?.value === "None") searchInput.value = "";
  searchForm?.addEventListener("submit", function (e) {
    if (!searchInput.value.trim()) {
      e.preventDefault();
      const url = new URL(window.location.href);
      url.searchParams.delete("q");
      window.location.href = url.toString();
    }
  });

  // ── EDIT mode ─────────────────────────────────────────────────────────────
  editBtn?.addEventListener("click", () => {
    if (table.classList.contains("select-mode")) return; // ignore if selecting
    table.classList.add("editing-mode");
    showContextButtons("edit");
  });

  // ── SAVE button ───────────────────────────────────────────────────────────
  saveBtn?.addEventListener("click", () => {
    const studentsData = [];
    document.querySelectorAll("#studentsTable tbody tr").forEach(row => {
      const data = { id: row.dataset.id };
      row.querySelectorAll(".editable").forEach(cell => {
        const input = cell.querySelector("input");
        if (cell.dataset.field && input) data[cell.dataset.field] = input.value;
      });
      studentsData.push(data);
    });
    studentsDataInput.value = JSON.stringify(studentsData);
    showToast("Student(s) updated successfully");
    editForm.submit();
  });

  // ── SELECT mode ───────────────────────────────────────────────────────────
  toggleBtn?.addEventListener("click", () => {
    if (table.classList.contains("editing-mode")) return; // ignore if editing
    table.classList.add("select-mode");
    showContextButtons("select");
  });

  // ── DELETE button ─────────────────────────────────────────────────────────
  deleteBtn?.addEventListener("click", () => {
    const anyChecked = document.querySelectorAll('input[name="selected_students"]:checked').length > 0;
    if (!anyChecked) {
      showToast("Select at least one student first.", "error");
      return;
    }
    confirmDeleteModal.show();
  });

  confirmDeleteBtn?.addEventListener("click", () => {
    showToast("Student(s) deleted successfully");
    deleteForm.submit();
  });

  document.getElementById("select-all")?.addEventListener("change", function () {
    document.querySelectorAll('input[name="selected_students"]')
      .forEach(cb => cb.checked = this.checked);
  });

  // ── CANCEL ────────────────────────────────────────────────────────────────
  cancelBtn?.addEventListener("click", () => {
    if (table.classList.contains("editing-mode")) {
      table.classList.remove("editing-mode");
      // Restore original values
      document.querySelectorAll(".editable").forEach(cell => {
        const span  = cell.querySelector("span");
        const input = cell.querySelector("input");
        if (span && input) input.value = span.textContent.trim();
      });
    }
    if (table.classList.contains("select-mode")) {
      table.classList.remove("select-mode");
      document.querySelectorAll('input[name="selected_students"]')
        .forEach(cb => cb.checked = false);
      document.getElementById("select-all") && (document.getElementById("select-all").checked = false);
    }
    showContextButtons(null);
  });
});