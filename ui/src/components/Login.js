import React, { useEffect, useState } from "react";
import {
    Button,
    Form,
    Grid,
    Header,
    Icon,
    Image,
    Message,
    Segment,
} from "semantic-ui-react";

const LoginForm = () => {
    // TODO, pull login configuraiton and render login page based on it.
    useEffect(() => {
        document.title = "Welcome to ConsoleMe - Please Sign-In";
    }, []);

    return (
        <>
            <Grid
                textAlign="center"
                verticalAlign="middle"
                style={{
                    height: "100vh",
                }}
            >
                <Grid.Column
                    style={{
                        maxWidth: 380,
                    }}
                >
                    <Header
                        attached="top"
                        block
                        textAlign="left"
                        style={{
                            fontSize: "34px",
                            textTransform: "uppercase",
                        }}
                    >
                        <Image
                            src="/images/logos/logo192.png"
                        />
                        ConsoleMe
                    </Header>
                    <Segment
                        attached
                        textAlign="left"
                    >
                        <Form size="small">
                            <Form.Input
                                fluid
                                icon="user"
                                iconPosition="left"
                                placeholder="E-mail address"
                                label="Username or email"
                            />
                            <Form.Input
                                fluid
                                icon="lock"
                                iconPosition="left"
                                placeholder="Password"
                                type="password"
                                label="Password"
                            />
                            <Button color="red" fluid size="large">
                                Sign in
                            </Button>
                            <p>
                                Only admins can add you to ConsoleMe for login. Please contact &nbsp;
                                <a href="#">infrasec@netflix.com</a> for console access.
                            </p>
                        </Form>
                    </Segment>
                    <Segment
                        attached
                        textAlign="left"
                    >
                        <p>
                            Single Sign-On is enabled for your organization.
                        </p>
                        <Button
                            color="green"
                            fluid
                        >
                            Sign In With Your Identity Provider
                        </Button>
                    </Segment>
                    <Message attached="bottom">
                        New to us? <a href="#">Sign Up</a>
                    </Message>
                </Grid.Column>
            </Grid>
            <Image
                disabled
                src="/images/logos/sunglasses/3.png"
                size="medium"
                style={{
                    bottom: 0,
                    right: 0,
                    position: "absolute",
                    marginRight: "10px",
                    marginBottom: "10px"
                }}
            />
        </>
    );
};
export default LoginForm;
