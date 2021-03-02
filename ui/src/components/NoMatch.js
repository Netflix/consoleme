import { Button, Header, Image, Segment } from "semantic-ui-react";
import { Link } from "react-router-dom";

const NoMatch = () => {
  return (
    <Segment
      basic
      style={{
        paddingTop: "120px",
        marginTop: "72px",
      }}
      textAlign="center"
    >
      <Header
        as="h1"
        color="grey"
        style={{
          fontSize: "74px",
        }}
        textAlign="center"
      >
        404
        <Header.Subheader>We were unable to console you!</Header.Subheader>
      </Header>
      <Image
        centered
        disabled
        size="medium"
        src="/images/logos/quarantine/1.png"
      />
      <br />
      <Link to="/">
        <Button content="Return to Home" color="red" size="large" />
      </Link>
    </Segment>
  );
};

export default NoMatch;
