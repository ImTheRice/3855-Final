import React, { useEffect, useState } from 'react';
import '../App.css';

export default function EndpointAudit(props) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [log, setLog] = useState({});
    const [error, setError] = useState(null);
    const [index, setIndex] = useState(getRandomIndex());

    function getRandomIndex() {
        return Math.floor(Math.random() * 100); // Adjust range as needed
    }

    useEffect(() => {
        const fetchAuditEvent = async () => {
            const newIndex = getRandomIndex(); // Get a new index
            setIndex(newIndex); // Update the state

            const url = `http://acit3855group4kafka.eastus2.cloudapp.azure.com/audit_log/audit/${props.endpoint}/${newIndex}`;

            try {
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setLog(data);
                setError(null); // Reset error state on success
            } catch (error) {
                setError(error);
                console.error("Error fetching data: ", error.message);
            } finally {
                setIsLoaded(true); // Set isLoaded to true regardless of success or error
            }
        };

        fetchAuditEvent();
        const interval = setInterval(fetchAuditEvent, 2000); // Retry every 2 seconds

        return () => clearInterval(interval); // Cleanup interval on unmount
    }, [props.endpoint]); // Dependency array includes props.endpoint

    // JSX to render
    if (error) {
        return <div className="error">Error: {error.message}</div>;
    } else if (!isLoaded) {
        return <div>Loading...</div>;
    } else {
        return (
            <div>
                <h3>{props.endpoint} - Index {index}</h3>
                <pre>{JSON.stringify(log, null, 2)}</pre>
            </div>
        );
    }
}

