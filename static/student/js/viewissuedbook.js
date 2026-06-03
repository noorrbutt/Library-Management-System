document.addEventListener('DOMContentLoaded', function() {
    // Initialize elements
    const returnButtons = document.querySelectorAll('.return-btn');
    const returnModal = new bootstrap.Modal(document.getElementById('returnModal'));
    const returnForm = document.getElementById('returnForm');
    const modalStudentName = document.getElementById('modalStudentName');
    const modalBookName = document.getElementById('modalBookName');
    
    const editBtn = document.getElementById('editBtn');
    const saveBtn = document.getElementById('saveBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const issuedBooksTable = document.getElementById('issuedBooksTable');
    
    let isEditMode = false;
    let originalData = {};

    // Return book functionality
    returnButtons.forEach(button => {
        button.addEventListener('click', function() {
            const issuedBookId = this.getAttribute('data-issuedbook-id');
            const studentName = this.getAttribute('data-student-name');
            const bookName = this.getAttribute('data-book-name');
            
            modalStudentName.textContent = studentName;
            modalBookName.textContent = bookName;
            
            // Set the hidden field value instead of modifying the form action
            document.getElementById('returnIssuedBookId').value = issuedBookId;
            
            returnModal.show();
        });
    });

    // Edit mode functionality
    if (editBtn) {
        editBtn.addEventListener('click', enableEditMode);
    }
    
    if (saveBtn) {
        saveBtn.addEventListener('click', saveChanges);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelEdit);
    }

    function enableEditMode() {
        if (isEditMode) return;
        
        isEditMode = true;
        issuedBooksTable.classList.add('edit-mode');
        editBtn.style.display = 'none';
        saveBtn.style.display = 'block';
        cancelBtn.style.display = 'block';
        
        // Store original values
        originalData = {};
        document.querySelectorAll('.editable-field').forEach(field => {
            const rowId = field.closest('tr').getAttribute('data-issuedbook-id');
            const fieldName = field.getAttribute('name');
            const key = `${rowId}_${fieldName}`;
            originalData[key] = field.value;
        });
    }

    function cancelEdit() {
        disableEditMode();
        restoreOriginalValues();
    }

    function disableEditMode() {
        isEditMode = false;
        issuedBooksTable.classList.remove('edit-mode');
        editBtn.style.display = 'block';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
    }

    function restoreOriginalValues() {
        document.querySelectorAll('.editable-field').forEach(field => {
            const rowId = field.closest('tr').getAttribute('data-issuedbook-id');
            const fieldName = field.getAttribute('name');
            const key = `${rowId}_${fieldName}`;
            if (originalData[key]) {
                field.value = originalData[key];
            }
        });
    }

    function saveChanges() {
        const booksData = [];
        const rows = issuedBooksTable.querySelectorAll('tr[data-issuedbook-id]');
        
        rows.forEach(row => {
            const issuedBookId = row.getAttribute('data-issuedbook-id');
            const bookData = {
                id: issuedBookId,
                student_name: row.querySelector('input[name="student_name"]').value,
                enrollment: row.querySelector('input[name="enrollment"]').value,
                book_name: row.querySelector('input[name="book_name"]').value,
                issue_date: row.querySelector('input[name="issue_date"]').value,
                return_date: row.querySelector('input[name="return_date"]').value
            };
            booksData.push(bookData);
        });

        // Send data to server
        const updateUrl = document.getElementById('update-issued-books-url').value;
        
        fetch(updateUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCSRFToken()
            },
            body: `books_data=${encodeURIComponent(JSON.stringify(booksData))}`
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Error saving changes');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving changes');
        });
    }

    function getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }
});