import React, { Component } from 'react';
import SelfServiceComponentEC2 from "./SelfServiceComponentEC2";
import SelfServiceComponentRDS from "./SelfServiceComponentRDS";
import SelfServiceComponentRoute53 from "./SelfServiceComponentRoute53";
import SelfServiceComponentS3 from './SelfServiceComponentS3';

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = 's3';


class SelfServiceComponent extends Component {
    // TODO(heewonk), load available components via dynamic import using module name pattern.
    static components = {
        ec2: SelfServiceComponentEC2,
        rds: SelfServiceComponentRDS,
        route53: SelfServiceComponentRoute53,
        s3: SelfServiceComponentS3,
    };

    componentDidMount() {
        // TODO(heewonk), retrieve a config from backend to figure which components to register.
    }

    render() {
        const Component = SelfServiceComponent.components[this.props.service || DEFAULT_AWS_SERVICE];
        return <Component {...this.props} />;
    }
}

export default SelfServiceComponent;