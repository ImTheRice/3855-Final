import logo from './logo.png';
import './App.css';

import EndpointAudit from './components/EndpointAudit'
import AppStats from './components/AppStats'
import Lazy from './components/Lazy';

function getRandomIndex() {
  // Implement the logic to return a random index
  return Math.floor(Math.random() * 100);
}


function App() {

    const endpoints = [
        { name: 'vehicle-status', index: getRandomIndex() },
        { name: 'incident-report', index: getRandomIndex() }
    ];

    const rendered_endpoints = endpoints.map((endpoint) => {
        return <EndpointAudit key={endpoint.name} endpoint={endpoint.name} index={endpoint.index} />;
    });

    return (
        <div className="App">
            <img src={logo} className="App-logo" alt="logo" height="150px" width="400px"/>
            <div>
                <AppStats/>
                <h1>Audit Endpoints</h1>
                {rendered_endpoints}
	        <Lazy />
            </div>
        </div>
    );

}


export default App;
