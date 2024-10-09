const host_base_url = "http://localhost:8000";
const crypto = require('crypto');

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

        // Get the response as plain text and return it
        const publicKey = await response.text();
        return publicKey;  // Return the public key
    } catch (error) {
        console.error("Error -> ", error);
    }
}

function encrypt_parametter(data, publicKey) {
    try {
        // Convert the data into a buffer
        const buffer = Buffer.from(data, 'utf-8');

        // Encrypt the data using the public key and OAEP padding with SHA-256
        const encrypted = crypto.publicEncrypt(
            {
                key: publicKey,
                padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,  // Use OAEP padding
                oaepHash: 'sha256',  // Use SHA-256 hash function
            },
            buffer
        );

        // Return the encrypted data as a base64 string (to match the backend)
        return encrypted.toString('base64');
    } catch (error) {
        console.error("Encryption error ->", error);
        throw error;
    }
}

async function set_user_credentials(account_id) {
    const public_key = await get_public_key(); 

    // In this part you should take the values from the needed fields
    const apikey = "my-apikey";
    const secret_key = "my-secret-key";
    const passphrase = "my-passphrase123";

    // Encrypt sensitive data using the public key
    const encrypted_apikey = encrypt_parametter(apikey, public_key); 
    const encrypted_secretkey = encrypt_parametter(secret_key, public_key);
    const encrypted_passphrase = encrypt_parametter(passphrase, public_key);

    console.log("encrypted apikey -> ", encrypted_apikey);
    console.log("encrypted secretkey -> ", encrypted_secretkey);
    console.log("encrypted passphrase -> ", encrypted_passphrase);

    // Prepare the data to be sent to the backend
    const url = `${host_base_url}/set_userkeys`;
    const data = {
        'account_id': account_id,
        'encrypted_apikey': encrypted_apikey,
        'encrypted_secret_key': encrypted_secretkey,
        'encrypted_passphrase': encrypted_passphrase
    };

    // Send the encrypted data to the backend
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify(data)  
        });

        // Handle the response
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }

        const result = await response.json();  // Parse the response as JSON
        console.log("Success:", result);  // Log success result
    } catch (error) {
        console.error("Error submitting credentials:", error);  // Handle errors
    }
}

// Start the process
set_user_credentials(account_id);
