import React, { useState } from 'react';
import {
    Accordion,
    Button,
    Label,
    Header,
    Segment,
    Tab
} from 'semantic-ui-react';
import { useParams } from "react-router-dom";
import MonacoEditor from "react-monaco-editor";


const ResourcePolicy = () => {
    return (
        <Header as="h2">
            Edit Resource Policy
        </Header>
    );
};

export default ResourcePolicy;