import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import _ from "lodash";
import {Button, Dimmer, Loader, Form, Grid, Header, Message, Search, Segment, Icon, Feed} from "semantic-ui-react";
import {sendRequestCommon} from "../helpers/utils";

const clone_options = [
    { text: "Assume Role Policy Document", value: "assume_role_policy"},
    { text: "Description", value: "copy_description"},
    { text: "Inline policies", value: "inline_policies"},
    { text: "Managed Policies", value: "managed_policies"},
    { text: "Tags", value: "tags"}
]

class CloneService extends Component {
    state = {
        isLoading: false,
        isLoadingAccount: false,
        results: [],
        resultsAccount: [],
        value: '',
        source_role: null,
        source_role_value: '',
        dest_account_id: null,
        dest_account_id_value: '',
        dest_role_name: '',
        searchType: '',
        description: '',
        messages: null,
        requestSent: false,
        requestResults: [],
        isSubmitting: false,
        roleCreated: false,
        options: [],
        copy_description: false
    }

    handleSearchChange(event, {name, value}) {
        if(name === 'source_role'){
            this.setState({
                isLoading: true,
                value,
                source_role_value: value,
                source_role: null,
                //TODO(jdhulia): fix the backend so that iam_arn can be used for typeahead
                searchType: 'app'
            });
        } else {
            this.setState({
                isLoadingAccount: true,
                value,
                dest_account_id_value: value,
                dest_account_id: null,
                searchType: 'account'
            });
        }

        setTimeout(() => {
            const {value, searchType} = this.state;
            if (value.length < 1) {
                return this.setState(
                    {
                        isLoading: false,
                        isLoadingAccount: false,
                        results: [],
                        value: '',
                        source_role: name === 'source_role' ? null : this.state.source_role,
                        source_role_value: name === 'source_role' ? '' : this.state.source_role_value,
                        dest_account_id: name === 'source_role' ? this.state.dest_account_id : null,
                        dest_account_id_value: name === 'source_role' ? this.state.dest_account_id_value : '',
                    }
                );
            }

            const re = new RegExp(_.escapeRegExp(value), 'i');
            const isMatch = (result) => re.test(result.title);

            const TYPEAHEAD_API = '/policies/typeahead?resource='+ searchType +'&search=' + value;

            fetch(TYPEAHEAD_API).then((resp) => {
                resp.json().then((source) => {
                    if(searchType === 'account') {
                        this.setState({
                            isLoadingAccount: false,
                            resultsAccount: source.filter(function (result) {
                                return re.test(result.title);
                            }),
                        });
                    } else {
                        const filteredResults = _.reduce(
                            source,
                            (memo, data, name) => {
                                const results = _.filter(data.results, isMatch);
                                if (results.length) {
                                    memo[name] = {name, results};
                                }
                                return memo;
                            },
                            {},
                        );
                        this.setState({
                            isLoading: false,
                            results: filteredResults,
                        });
                    }

                });
            });
        }, 300);
    }

    handleSubmit(){

        const {source_role, dest_account_id, dest_role_name} = this.state
        let errors = []
        if(!source_role){
            errors.push("No source role provided, please select a source role")
        }
        if(!dest_account_id){
            errors.push("No destination account provided, please select a destination account")
        }
        if(dest_role_name === ""){
            errors.push("No destination role name provided, please provide a destination role name")
        }
        if(errors.length > 0){
            return this.setState({
                messages: errors,
            });
        }

        const cloneOptions = {
            "assume_role_policy": this.state.options.includes("assume_role_policy"),
            "tags": this.state.options.includes("tags"),
            "copy_description": this.state.options.includes("copy_description"),
            "description": this.state.description,
            "inline_policies": this.state.options.includes("inline_policies"),
            "managed_policies": this.state.options.includes("managed_policies")
        }

        const payload = {
            "account_id": source_role.substring(13, 25),
            "role_name": source_role.substring(source_role.indexOf("/", 25) + 1),
            "dest_account_id": dest_account_id.substring(dest_account_id.indexOf("(") + 1, dest_account_id.indexOf(")")),
            "dest_role_name": this.state.dest_role_name,
            "options": cloneOptions
        }
        this.setState({
            messages: null,
            isSubmitting: true,
            dest_account_id: payload["dest_account_id"]
        }, async() => {
            const response = await sendRequestCommon(
                JSON.stringify(payload),
                '/api/v2/clone/role',
            );
            const messages = []
            let requestResults = []
            let requestSent = false;
            let roleCreated = false;
            if(response){
                requestSent = true
                if(!response.hasOwnProperty("role_created")){
                    requestResults.push({
                        "Status": "error",
                        "message": response.message
                    })
                } else {
                    requestResults = response.action_results
                    if(response.role_created === "true"){
                        roleCreated = true
                    }
                }
            } else {
                messages.push("Failed to submit cloning request");
            }
            this.setState({
                isSubmitting: false,
                messages,
                requestSent,
                requestResults,
                roleCreated
            });
        })
    }

    handleResultSelect(e, {name, value_name, result}) {
        this.setState({
            [value_name]: result.title,
            [name]: result.title,
            isLoading: false
        });
    }

    handleDropdownChange(e, {value}){
        this.setState({
            options: value,
            copy_description: value.includes("copy_description")
        })
    }
    handleChange = (e, { name, value }) => this.setState({ [name]: value })

    handleCheckChange = (e, {name, value}) => this.setState({ [name]: !value})

    render() {
       const {isLoading, isLoadingAccount, results, source_role_value, dest_account_id_value, dest_role_name, resultsAccount,
              description, messages, requestSent, requestResults,
              isSubmitting, roleCreated, dest_account_id, copy_description} = this.state;
       const messagesToShow = (messages != null && messages.length > 0)
            ? (
                <Message negative>
                    <Message.Header>
                        There are some missing parameters
                    </Message.Header>
                    <Message.List>
                        {
                            messages.map(message => {
                                return <Message.Item>{message}</Message.Item>;
                            })
                        }
                    </Message.List>
                </Message>
            )
            : null;

       const preRequestContent =
           (
               <Segment.Group vertical>
                   <Segment>
                       <Grid columns={2} divided>
                            <Grid.Row>
                                <Grid.Column>
                                    <Header size='medium'>
                                            Select source role
                                            <Header.Subheader>
                                                Please search for the role you want to clone.
                                            </Header.Subheader>
                                    </Header>
                                    <Form widths="equal">
                                        <Form.Field required>
                                            <label>Source Role</label>
                                            <Search
                                                category
                                                loading={isLoading}
                                                name='source_role'
                                                value_name='source_role_value'
                                                onResultSelect={this.handleResultSelect.bind(this)}
                                                onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
                                                    leading: true,
                                                })}
                                                results={results}
                                                value={source_role_value}
                                            >
                                            </Search>
                                        </Form.Field>
                                        <Form.Dropdown
                                            placeholder='Options'
                                            fluid
                                            multiple
                                            search
                                            selection
                                            options={clone_options}
                                            label="Attributes to clone"
                                            onChange={this.handleDropdownChange.bind(this)}
                                        />
                                    </Form>
                                </Grid.Column>
                                <Grid.Column>
                                    <Header size='medium'>
                                            Destination role
                                            <Header.Subheader>
                                                Please enter the destination account where you want the cloned role and desired role name.
                                            </Header.Subheader>
                                    </Header>
                                    <Form widths='equal'>
                                            <Form.Field required>
                                                <label>Account ID</label>
                                                <Search
                                                    loading={isLoadingAccount}
                                                    name='dest_account_id'
                                                    value_name='dest_account_id_value'
                                                    onResultSelect={this.handleResultSelect.bind(this)}
                                                    onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
                                                        leading: true,
                                                    })}
                                                    results={resultsAccount}
                                                    value={dest_account_id_value}
                                                />
                                            </Form.Field>
                                            <Form.Input required fluid label='Role name' name='dest_role_name'
                                                        value={dest_role_name} placeholder='Role name'
                                                        onChange={this.handleChange}
                                            />
                                            <Form.Input required fluid name='description'
                                                value={description} placeholder='Optional description'
                                                onChange={this.handleChange}
                                                disabled={true === copy_description}
                                            />
                                    </Form>
                                </Grid.Column>
                            </Grid.Row>
                       </Grid>
                   </Segment>
                <Segment>
                        {messagesToShow}
                        <Button
                            content="Submit"
                            fluid
                            onClick={this.handleSubmit.bind(this)}
                            primary
                        />
                </Segment>
               </Segment.Group>
       )

       const postRequestContent = (requestResults.length > 0) ?
           (
               <Segment>
                   <Feed>
                       {requestResults.map(result => {
                            const iconLabel = (result.status === "success") ? (<Icon name='checkmark' color="teal"/>) : (<Icon name='close' color="pink" />)
                            const feedResult = (result.status === "success") ? "Success" : "Error"
                            return <Feed.Event>
                                        <Feed.Label>
                                            {iconLabel}
                                        </Feed.Label>
                                        <Feed.Content>
                                            <Feed.Date>{feedResult}</Feed.Date>
                                            <Feed.Summary>{result.message}</Feed.Summary>
                                        </Feed.Content>
                                    </Feed.Event>
                            })
                       }
                   </Feed>
               </Segment>
           )
           :
           null;

       const roleInfoLink = (roleCreated) ?
           (<Message info>
               The requested role has been created. You can view the role details <a href={`/policies/edit/${dest_account_id}/iamrole/${dest_role_name}`} target="_blank">here</a>.
           </Message>)
           :
           null;

       const pageContent = (requestSent) ? postRequestContent : preRequestContent;

       return (
            <React.Fragment>
                <Dimmer
                    active={isSubmitting}
                    inverted
                >
                    <Loader />
                </Dimmer>
                <Segment>
                    <Header size='huge'>
                        Clone a role
                    </Header>
                </Segment>
                {roleInfoLink}
                {pageContent}
            </React.Fragment>
        )
    }
}


export function renderCloneWizard() {
    ReactDOM.render(
        <CloneService />,
        document.getElementById("clone_wizard"),
    );
}

export default CloneService;