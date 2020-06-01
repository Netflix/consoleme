import React, {Component} from 'react';


class SelfServiceComponentCustom extends Component {
    static TYPE = 'custom';
    static NAME = 'Custom Permission (Advanced)';

    state = {
    };

    componentDidMount() {
        // initialize a permission state
        this.props.updatePermission({
            type: SelfServiceComponentCustom.TYPE,
        });
    }

    render() {

        return (
            <p>
                Custom Fields
            </p>
        );
    }
}

export default SelfServiceComponentCustom;
