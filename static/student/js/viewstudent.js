// static/student/js/viewstudent.js
document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn         = document.getElementById("toggle-btn");
  const editBtn           = document.getElementById("edit-btn");
  const cancelBtn         = document.getElementById("cancel-btn");
  const filterBtn         = document.getElementById("filter-btn");
  const filterCollapse    = document.getElementById("filterCollapse");
  const table             = document.getElementById("studentsTable");
  const deleteForm        = document.getElementById("student-form");
  const editForm          = document.getElementById("edit-form");
  const studentsDataInput = document.getElementById("students-data");
  const confirmDeleteBtn  = document.getElementById("confirmDeleteBtn");
  const confirmDeleteModal = new bootstrap.Modal(document.getElementById("confirmDeleteModal"));

  // ── Toast ──────────────────────────────────────────────────────────────────
  const actionToast   = document.getElementById("actionToast");
  const toastMessage  = document.getElementById("toastMessage");
  const bsToast       = actionToast ? new bootstrap.Toast(actionToast, { delay: 3000 }) : null;

  function showToast(message, type = "success") {
    if (!bsToast) return;
    actionToast.classList.remove("bg-success", "bg-danger");
    actionToast.classList.add(type === "success" ? "bg-success" : "bg-danger");
    toastMessage.textContent = message;
    bsToast.show();
  }

  // ── Filter toggle ──────────────────────────────────────────────────────────
  filterBtn?.addEventListener("click", () => {
    const isOpen = filterCollapse.style.display === "block";
    filterCollapse.style.display = isOpen ? "none" : "block";
    filterBtn.innerHTML = isOpen
      ? '<i class="fas fa-filter"></i>Filter'
      : '<i class="fas fa-times"></i>Close Filter';
  });

  // ── Search: don't submit empty q ───────────────────────────────────────────
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

  // ── Edit / Save ────────────────────────────────────────────────────────────
  editBtn?.addEventListener("click", () => {
    if (table.classList.contains("editing-mode")) {
      saveInlineEdits();
    } else {
      // Exit select mode if active before entering edit mode
      if (table.classList.contains("select-mode")) {
        table.classList.remove("select-mode");
        toggleBtn.innerHTML = '<i class="fas fa-check-square"></i>Select';
        document.getElementById("delete-toolbar").style.display = "none";
        document.querySelectorAll('input[name="selected_students"]').forEach(cb => cb.checked = false);
      }
      table.classList.add("editing-mode");
      editBtn.innerHTML = '<i class="fas fa-save"></i>Save';
      cancelBtn.classList.remove("d-none");
    }
  });

  cancelBtn?.addEventListener("click", () => {
    if (table.classList.contains("editing-mode")) {
      table.classList.remove("editing-mode");
      editBtn.innerHTML = '<i class="fas fa-edit"></i>Edit';
      cancelBtn.classList.add("d-none");
      resetInlineEdits();
    } else if (table.classList.contains("select-mode")) {
      table.classList.remove("select-mode");
      toggleBtn.innerHTML = '<i class="fas fa-check-square"></i>Select';
      document.getElementById("delete-toolbar").style.display = "none";
      document.querySelectorAll('input[name="selected_students"]').forEach(cb => cb.checked = false);
      cancelBtn.classList.add("d-none");
    }
  });

  function saveInlineEdits() {
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
  }

  function resetInlineEdits() {
    document.querySelectorAll(".editable").forEach(cell => {
      const span  = cell.querySelector("span");
      const input = cell.querySelector("input");
      if (span && input) input.value = span.textContent.trim();
    });
  }

  // ── Select / Delete ────────────────────────────────────────────────────────
  toggleBtn?.addEventListener("click", () => {
    const isSelecting = table.classList.toggle("select-mode");
    // Exit edit mode if active before entering select mode
    if (isSelecting && table.classList.contains("editing-mode")) {
      table.classList.remove("editing-mode");
      editBtn.innerHTML = '<i class="fas fa-edit"></i>Edit';
      resetInlineEdits();
    }
    toggleBtn.innerHTML = isSelecting
      ? '<i class="fas fa-times"></i>Cancel Select'
      : '<i class="fas fa-check-square"></i>Select';
    document.getElementById("delete-toolbar").style.display = isSelecting ? "block" : "none";
    cancelBtn.classList.toggle("d-none", !isSelecting);
    if (!isSelecting) {
      document.querySelectorAll('input[name="selected_students"]').forEach(cb => cb.checked = false);
    }
  });

  document.getElementById("delete-selected-btn")?.addEventListener("click", () => {
    confirmDeleteModal.show();
  });

  confirmDeleteBtn?.addEventListener("click", () => {
    showToast("Student(s) deleted successfully");
    deleteForm.submit();
  });

  document.getElementById("select-all")?.addEventListener("change", function () {
    document.querySelectorAll('input[name="selected_students"]').forEach(cb => cb.checked = this.checked);
  });
});