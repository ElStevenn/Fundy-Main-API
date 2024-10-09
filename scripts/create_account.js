const host_base_url = "http://localhost:8000";
const NodeRSA = require('node-rsa');

// Credentials
const user_id = "4e21db51-0e4d-47e2-bfc0-15ad00cb6c61";
const account_id = "56f78704-9045-435f-97d6-7d4d4b20cce2";


async function get_public_key() {
    const url = `${host_base_url}/security/get-public-key`;

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: { 'Accept': 'text/plain' }  
        });

        // Check if the response is okay (status code 200-299)
        if (!response.ok) {
            throw new Error(`Error fetching public key: ${response.statusText}`);
        }

        // Get the response as plain text
        const publicKey = await response.text();
        return publicKey;  // Return the public key
    } catch (error) {
        console.error("Error -> ", error);
    }
}

function encrypt_parametter(data, publicKey) {
    const key = new NodeRSA(publicKey, 'pkcs1-public');
    const encryptedData = key.encrypt(data, 'base64');
    return encryptedData; 
}

// Function to create a new account
async function create_new_account(params) {
    const url = `${host_base_url}/create_new_account/${user_id}`;
    
    try {
        const result = await fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify(params) 
        });

        // Check if the response is okay (status code 200-299)
        if (!result.ok) {
            throw new Error(`Error creating account: ${result.statusText}`);
        }

        const responseData = await result.json(); 
        console.log("Account creation response: ", responseData);
    } catch (error) {
        console.error("Error in create_new_account: ", error);
    }
}

async function set_user_credentials(account_id) {
    const public_key = await get_public_key(); 

    // In this part you should take the values from the needed fields
    const apikey = "my-apikey";
    const secret_key = "my-secret-key";
    const passphrase = "my-passphrase123";

    const encrypted_apikey = encrypt_parametter(apikey, public_key); 
    const encrypted_secretkey = encrypt_parametter(secret_key, public_key);
    const encrypted_passphrase = encrypt_parametter(passphrase, public_key);

    // Prepare the parameters to send
    const params = {
        encrypted_apikey,
        encrypted_secretkey,
        encrypted_passphrase
    };

    await create_new_account(params); 
}

// Start the process
const account = {
    'type': 'trading',
    'email': 'sfukinguay@gmail.com'
}
create_new_account(account);
