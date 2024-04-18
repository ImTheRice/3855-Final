// Lazy.js
import React, { useEffect, useState } from 'react';

const Lazy = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    const interval = setInterval(() => {
      fetch('http://acit3855group4kafka.eastus2.cloudapp.azure.com/event_logger/events_stats')
        .then((response) => response.json())
        .then((data) => {
          setData(data);
          console.log(data); // Or handle your data as needed
        })
        .catch((error) => {
          console.error('Error fetching data: ', error);
        });
    }, 2000); // fetch every 2 seconds

    return () => clearInterval(interval); // cleanup interval on unmount
  }, []); // empty dependency array means it runs once on mount

  return (
    <div>
      {data ? (
        <pre>{JSON.stringify(data, null, 2)}</pre> // Display data
      ) : (
        <p>Loading...</p> // Display a loading state
      )}
    </div>
  );
};

export default Lazy;

