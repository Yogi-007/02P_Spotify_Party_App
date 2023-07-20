import React, { Component } from "react";
import { Grid, Button, Typography } from "@material-ui/core";
import CreateRoomPage from "./CreateRoomPage";
import MusicPlayer from "./MusicPlayer";

export default class Room extends Component {
  // as we setup route path in home page we gave :roomCode now this will recive a prop called match that has the roomcode in the redirected url
  constructor(props) {
    super(props); // has a extra prop sent from HomePage called leaveRoomCallback/clearRoomCode to clear roomCode in homepage
    this.state = {
      votesToSkip: 2,
      guestCanPause: false,
      isHost: false,
      showSettings: false,
      spotifyAuthenticated: false,
      song: {},
    };
    // url roomCode to roomCode local viarable
    this.roomCode = this.props.match.params.roomCode; // sent via route url having code in props accessed via match
    this.leaveButtonPressed = this.leaveButtonPressed.bind(this);
    this.updateShowSettings = this.updateShowSettings.bind(this);
    this.renderSettingsButton = this.renderSettingsButton.bind(this);
    this.renderSettings = this.renderSettings.bind(this);
    this.getRoomDetails = this.getRoomDetails.bind(this);
    this.authenticateSpotify = this.authenticateSpotify.bind(this);
    this.getCurrentSong = this.getCurrentSong.bind(this);
    this.getRoomDetails();
    this.getCurrentSong();
  }
  //for hitting spotify current song every second
  componentDidMount() {
    this.interval = setInterval(this.getCurrentSong, 1000);
  }
  componentWillUnmount() {
    clearInterval(this.interval);
  }

  //render settings page upon state change
  //uses createroompage.js component updating its props ie its state items guestcanpause, votestoskip, roomcode
  //also passes an extra prop updatecallback when triggered in create room page by back will run here in room.js
  //also adds a button to createroom component called close settings which updates showsettings state here to false(rerenders fresh room page)
  renderSettings() {
    return (
      <Grid container spacing={1}>
        <Grid item xs={12} align="center">
          <CreateRoomPage
            update={true}
            votesToSkip={this.state.votesToSkip}
            guestCanPause={this.state.guestCanPause}
            roomCode={this.roomCode}
            updateCallback={this.getRoomDetails}
          />
        </Grid>
        <Grid item xs={12} align="center">
          <Button
            variant="contained"
            color="secondary"
            onClick={() => this.updateShowSettings(false)}
          >
            Close
          </Button>
        </Grid>
      </Grid>
    );
  }

  // sets the showsettings state to true/false
  updateShowSettings(value) {
    this.setState({
      showSettings: value,
    });
  }

  // renders a button for only the host,  will be called in the render function only when host
  // upon click calls updateshowsettings function to change the state showsettings to true
  renderSettingsButton() {
    return (
      <Grid item xs={12} align="center">
        <Button
          variant="contained"
          color="primary"
          onClick={() => this.updateShowSettings(true)}
        >
          Settings
        </Button>
      </Grid>
    );
  }

  // calls api end point leave room and redirects to home page
  leaveButtonPressed() {
    const requestOptions = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }; // sending call so that room is deteled if this is host and clearing session variable for both users
    fetch("/api/leave-room", requestOptions).then((_response) => {
      this.props.leaveRoomCallback(); // clears roomCode in state in home page
      this.props.history.push("/"); // then redirects to home page
    });
  }

  // gets current song details calling appropriate spotify view end point
  getCurrentSong() {
    fetch("/spotify/current-song")
      .then((response) => {
        if (!response.ok) {
          return {};
        } else {
          return response.json();
        }
      })
      .then((data) => {
        this.setState({ song: data });
        console.log(data);
      });
  }

  getRoomDetails() {
    fetch("/api/get-room" + "?code=" + this.roomCode)
      .then((response) => {
        if (!response.ok) {
          // if response is ok then only render the page by setting state @bottom
          // if room doesnt exist clear roomcode in homepage and then go back to home
          this.props.leaveRoomCallback();
          this.props.history.push("/");
        }
        return response.json(); //return error response from api GetRoom
      })
      .then((data) => {
        this.setState({
          //@bottom
          votesToSkip: data.votes_to_skip,
          guestCanPause: data.guest_can_pause,
          isHost: data.is_host,
        });
        if (this.state.isHost) {
          this.authenticateSpotify();
        }
      });
  }

  // calls IsAuthenticated End point and finds if False or True
  authenticateSpotify() {
    fetch("/spotify/is-authenticated")
      .then((response) => response.json())
      .then((data) => {
        this.setState({ spotifyAuthenticated: data.status });
        console.log(data.status);
        if (!data.status) {
          // if false meaning no entry new user, then send the url to spotify (hits callback)
          fetch("/spotify/get-auth-url") //hits AuthURL end point and gets the url
            .then((response) => response.json())
            .then((data) => {
              window.location.replace(data.url); // sending that url to auth , after auth spotify auto hits callback
            });
        }
      });
  }

  // render settings page if state showsettings is true else render a fresh room page
  render() {
    if (this.state.showSettings) {
      return this.renderSettings();
    }
    return (
      <Grid container spacing={1}>
        <Grid item xs={12} align="center">
          <Typography variant="h4" component="h4">
            Code: {this.roomCode}
          </Typography>
        </Grid>
        <MusicPlayer {...this.state.song} />
        {this.state.isHost ? this.renderSettingsButton() : null}
        {/* renders button if host else ntng */}
        <Grid item xs={12} align="center">
          <Button
            variant="contained"
            color="secondary"
            onClick={this.leaveButtonPressed}
          >
            Leave Room
          </Button>
        </Grid>
      </Grid>
    );
  }
}

/* 
<Grid item xs={12} align="center">
          <Typography variant="h6" component="h6">
            Votes : {this.state.votesToSkip}
          </Typography>
        </Grid>
        <Grid item xs={12} align="center">
          <Typography variant="h6" component="h6">
            Guest Control : {this.state.guestCanPause.toString()}
          </Typography>
        </Grid>
        <Grid item xs={12} align="center">
          <Typography variant="h6" component="h6">
            Host : {this.state.isHost.toString()}
          </Typography>
        </Grid>
*/
