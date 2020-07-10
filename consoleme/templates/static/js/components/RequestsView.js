import React, {Component, useState, useEffect}  from 'react';
import ReactDOM from "react-dom";
import CreateCloneFeature from "./CreateCloneFeature";

export default function RequestsView() {
    const [data, setData] = useState([])
    const [q, setQ] = useState("")

    useEffect(() => {
        // function we want to fire when dependency is triggered
        fetch("/api/v2/requests")
            .then(response => response.json())
            .then(json => setData(json))
    }, [])
    return (
        <div>
            LOL
            <div>FILTER</div>
            <div>DATATABLE</div>
            {setData}
            {data}
        </div>
    )
}

export function renderRequestsView() {
    ReactDOM.render(
        <RequestsView />,
        document.getElementById("requests_view"),
    );
}
