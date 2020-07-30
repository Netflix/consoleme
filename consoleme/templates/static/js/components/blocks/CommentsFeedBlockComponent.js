import React, {Component} from 'react';
import {
    Button, Comment, Divider, Feed, Header, Icon, Image, Input, Segment
} from 'semantic-ui-react';


class CommentsFeedBlockComponent extends Component {
    constructor(props) {
        super(props);
        this.state = {
            comments: this.props.comments,
            isLoading: false,
            commentText: "",
            messages: []
        };
    }

    handleCommentChange(e) {
        this.setState({
            commentText: e.target.value,
        });
    }

    handleSubmitComment(e){
        const {commentText} = this.state;
        this.setState({
            isLoading: true
        }, () => {
            // TODO: make request to backend to add comment
            console.log(commentText);
            this.setState({
                isLoading: false,
                commentText: ""
            })
        })
    }

    render() {
        const {comments, commentText, isLoading} = this.state;

        const commentsContent = (comments && comments.length > 0) ?
            (
                <Comment.Group>
                            {comments.map((comment) =>
                                <Comment>
                                    {comment.user && comment.user.extended_info && comment.user.extended_info.thumbnailPhotoUrl ?
                                        <Comment.Avatar src={comment.user.extended_info.thumbnailPhotoUrl} />
                                        :
                                        //TODO: change to some default image
                                        <Comment.Avatar src={"/static/logos/sunglasses/1.png"} />
                                    }

                                  <Comment.Content>
                                      {comment.user && comment.user.details_url ?
                                          <Comment.Author as={'a'}>
                                            <a href={comment.user.details_url} target={"_blank"}>{comment.user_email}</a>
                                          </Comment.Author>
                                          :
                                          <Comment.Author as={'text'}>
                                              {comment.user_email}
                                          </Comment.Author>
                                      }
                                      <Comment.Metadata><div>{new Date(comment.timestamp).toLocaleString()}</div></Comment.Metadata>
                                        <Comment.Text>
                                            {comment.text}
                                        </Comment.Text>
                                        <Comment.Actions>
                                            <Comment.Action>
                                                <Divider />
                                            </Comment.Action>
                                        </Comment.Actions>
                                  </Comment.Content>
                                </Comment>
                            )}
                    </Comment.Group>
            )
            :
            null;

        const commentInput =
            (
                <Input
                    action={
                        <Button
                            content="Add comment"
                            primary
                            disabled={commentText === ""}
                            onClick={this.handleSubmitComment.bind(this)}
                        />
                    }
                    placeholder="Add a new comment..."
                    fluid
                    icon={'comment'}
                    iconPosition={'left'}
                    onChange={this.handleCommentChange.bind(this)}
                    loading={isLoading}
                    value={commentText}
                />
            )

        return <Segment>
                    <Header size={'medium'}>
                        Comments <Icon name='comments'/>
                    </Header>
                    {commentsContent}
                    {commentInput}
                </Segment>

    }
}

export default CommentsFeedBlockComponent;
