console.log("HEY!");

const url_base = 'http://localhost/';

function get_all_tasks() {
    // Construct the URL for the GET request
    const url = url_base + "tasks";
    
    // Make a GET request to the specified URL
    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            return data;
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
        });
}

// Function to create a task element
function createTaskElement(taskId, task) {
    const taskElement = document.createElement('li');
    taskElement.innerHTML = `
        <div class="task-info">
            <span class="title">${task.type}</span>
            <a href="${task.url}" class="url">${task.url}</a>
        </div>
        <button class="delete-btn" onclick="deleteTask(this)">Delete</button>
    `;
    return taskElement;
}

// Populate the task list with fetched tasks
get_all_tasks().then(tasks => {
    const taskList = document.getElementById('task-list');
    if (Object.keys(tasks).length === 0) {
        // If no tasks, show "No tasks available" message
        const noTasksElement = document.createElement('li');
        noTasksElement.textContent = "No tasks available";
        taskList.appendChild(noTasksElement);
    } else {
        for (const [taskId, task] of Object.entries(tasks)) {
            const taskElement = createTaskElement(taskId, task);
            taskList.appendChild(taskElement);
        }
    }
});

// Function to delete a task
function deleteTask(button) {
    const li = button.parentElement;
    li.remove();
}
