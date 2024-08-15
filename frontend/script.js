console.log("HEY!");

const url_base = '/';  // Using a relative URL base

function createTaskElement(taskId, task) {
    const taskElement = document.createElement('li');
    taskElement.innerHTML = `
        <div class="task-info">
            <span class="title">${task.type}</span>
            <a href="${task.url}" class="url">TASK LOL -> ${task.url}</a>
        </div>
        <button class="delete-btn">Delete</button>
    `;
    
    // Adding the event listener programmatically
    const deleteButton = taskElement.querySelector('.delete-btn');
    deleteButton.addEventListener('click', () => deleteTask(deleteButton, taskId));
    
    return taskElement;
}

// Function to convert snake_case to Title Case
function convertToTitleCase(str) {
    return str.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
}

// Function to create a text input
function createInput(id, label, type, value) {
    return `
        <div class="config-group">
            <label for="${id}">${label}:</label>
            <input type="${type}" id="${id}" value="${value}">
        </div>
    `;
}

// Function to create a switch (checkbox)
function createSwitch(id, label, checked) {
    return `
        <div class="config-group">
            <label for="${id}">${label}:</label>
            <label class="switch">
                <input type="checkbox" id="${id}" ${checked ? 'checked' : ''}>
                <span class="slider"></span>
            </label>
        </div>
    `;
}

// Function to dynamically populate the form based on the configuration JSON
function populateConfigForm(config) {
    if (!config) return;

    const form = document.getElementById('config-form');
    let formHTML = '';

    // Iterate over each key in the JSON
    Object.keys(config).forEach(key => {
        const value = config[key];
        const label = convertToTitleCase(key);

        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            // If the value is an object, create a section for it
            formHTML += `<h3>${label}</h3>`;
            Object.keys(value).forEach(subKey => {
                const subValue = value[subKey];
                const subLabel = convertToTitleCase(subKey);
                if (typeof subValue === 'boolean') {
                    formHTML += createSwitch(`${key}_${subKey}`, subLabel, subValue);
                } else {
                    formHTML += createInput(`${key}_${subKey}`, subLabel, 'text', subValue);
                }
            });
        } else if (typeof value === 'boolean') {
            // If the value is a boolean, create a switch
            formHTML += createSwitch(key, label, value);
        } else {
            // Otherwise, create a text input
            formHTML += createInput(key, label, 'text', value);
        }
    });

    // Inject generated HTML into the form container
    form.innerHTML = formHTML;
}

// Function to fetch the configuration from the server
function get_config() {
    const url = '/conf';  // Using a relative URL for the configuration endpoint

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
            return null;  // Return null to handle errors gracefully
        });
}

// Fetch and populate the configuration data when the page loads
get_config().then(config => {
    populateConfigForm(config);
});

function saveConfig() {
    // Initialize an empty configuration object
    const config = {};

    // Select all input elements within the config-form container
    const formElements = document.querySelectorAll('#config-form input');

    // Iterate over each input element
    formElements.forEach(input => {
        const [key, subKey] = input.id.split('_');  // Split the ID by underscore

        if (subKey) {
            // If it's a nested property, ensure the object exists
            if (!config[key]) {
                config[key] = {};
            }

            // Set the value based on the input type
            if (input.type === 'checkbox') {
                console.log(`Mapping boolean: ${key}_${subKey} = ${input.checked}`);
                config[key][subKey] = input.checked;
            } else {
                console.log(`Mapping value: ${key}_${subKey} = ${input.value}`);
                config[key][subKey] = input.value;
            }
        } else {
            // If it's a top-level property
            if (input.type === 'checkbox') {
                console.log(`Mapping boolean: ${key} = ${input.checked}`);
                config[key] = input.checked;
            } else {
                console.log(`Mapping value: ${key} = ${input.value}`);
                config[key] = input.value;
            }
        }
    });

    console.log("Final config object:", JSON.stringify(config, null, 2));  // Debugging: Check the final config object

    // Send the configuration object to the server
    fetch('/save-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
    })
    .then(response => {
        if (!response.ok) {
            // If the server responds with a non-OK HTTP status, throw an error
            throw new Error('Network response was not ok');
        }
        return response.json();  // Parse JSON response from the server
    })
    .then(data => {
        alert('Configuration saved successfully!');
    })
    .catch(error => {
        console.error('There was a problem with the save operation:', error);
        alert('Failed to save configuration.');
    });
}




function createTaskElement(taskId, task) {
    const taskElement = document.createElement('li');
    if (task.type === "interval_minutes_task"){
        taskElement.innerHTML = `
        <div class="task-info">
            <span class="title">${task.type}</span>
            <a href="${task.url}" class="url">${task.url}</a>
        </div>
        <button class="delete-btn">Delete</button>
    `;
    }else if(task.type === "interval_tasks_unlimited"){
        taskElement.innerHTML = `
        <div class="task-info">
            <span class="title">${task.type}</span>
            <a href="${task.url}" class="url">${task.url}</a>
        </div>
        <button class="delete-btn">Delete</button>
    `;
    }else if(task.type === "interval_minutes_task"){
        taskElement.innerHTML = `
        <div class="task-info">
            <span class="title">${task.type}</span>
            <a href="${task.url}" class="url">${task.url}</a>
        </div>
        <button class="delete-btn">Delete</button>
        `;
    }

    
    // Adding the event listener programmatically
    const deleteButton = taskElement.querySelector('.delete-btn');
    deleteButton.addEventListener('click', () => deleteTask(deleteButton, taskId));
    
    return taskElement;
}

function get_all_tasks() {
    const url = url_base + 'tasks';  // Update the URL to the correct endpoint

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
            return {};  // Return an empty object to handle errors gracefully
        });
}


// Populate the task list with fetched tasks
get_all_tasks().then(tasks => {
    const taskList = document.getElementById('task-list');
    
    if (!tasks || Object.keys(tasks).length === 0) {
        const noTasksElement = document.createElement('li');
        noTasksElement.textContent = "No tasks available";
        taskList.appendChild(noTasksElement);
    } else {
        console.log("Tasks fetched:", tasks); // Log the tasks fetched
        for (const [taskId, task] of Object.entries(tasks)) {
            console.log(`Processing task with ID: ${taskId}`); // Log each task
            const taskElement = createTaskElement(taskId, task);
            taskList.appendChild(taskElement);
        }
    }
}).catch(error => {
    console.error('Error handling tasks:', error);
});

// Function to delete a task
function deleteTask(button, taskId) {
    console.log(`Attempting to delete task with ID: ${taskId}`);  // Debugging

    const url = url_base + "delete_task/" + taskId;

    fetch(url, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            console.error(`Failed to delete task with ID: ${taskId}, Status: ${response.status}`);
            throw new Error('Failed to delete the task');
        }
        // Only call .text() if your server returns no content
        return response.text(); 
    })
    .then(() => {
        console.log('Task deleted successfully'); 
        // Remove the task from the DOM
        const li = button.closest('li');  
        if (li) {
            li.remove();
        } else {
            console.error('Could not find the parent <li> element to remove.');
        }
    })
    .catch(error => {
        console.error('Error deleting task:', error);
    });
}

