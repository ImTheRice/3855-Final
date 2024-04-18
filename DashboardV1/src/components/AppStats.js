import React, { useEffect, useState } from 'react';
import '../App.css';

export default function AppStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [stats, setStats] = useState({});
    const [error, setError] = useState(null);

    const getStats = () => {
        const url = `http://acit3855group4kafka.eastus2.cloudapp.azure.com/processing/events/stats`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                setStats(data);
                setIsLoaded(true);
            })
            .catch(err => {
                console.error("Error loading stats: ", err.message);
                setError(err);
                setIsLoaded(true);
            });
    };

    useEffect(() => {
        const interval = setInterval(getStats, 2000); // Update every 2 seconds
        return () => clearInterval(interval); // This will clear the interval when the component unmounts.
    }, []);

    if (error) {
        return <div className="error">Error: {error.message}</div>;
    } else if (!isLoaded) {
        return <div>Loading...</div>;
    } else {
        return (
            <div>
                <h1>Latest Stats</h1>
                <table className="StatsTable">
                    <tbody>
                        <tr>
                            <th>Vehicle Status Events</th>
                            <th>Incident Report Events</th>
                        </tr>
                        <tr>
                            <td>Total Vehicle Status Events: {stats.num_vehicle_status_events}</td>
                            <td>Total Incident Report Events: {stats.num_incident_events}</td>
                        </tr>
                        <tr>
                            <td>Max Distance Travelled: {stats.max_distance_travelled}</td>
                            <td>Max Incident Severity: {stats.max_incident_severity}</td>
                        </tr>
                    </tbody>
                </table>
                <h3>Last Updated: {stats.last_updated}</h3>
            </div>
        );
    }
}

