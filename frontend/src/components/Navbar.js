import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Timeline as TimelineIcon,
  Warning as WarningIcon,
  Psychology as PsychologyIcon,
} from '@mui/icons-material';

const Navbar = () => {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Netflow v5 Server
        </Typography>
        <Box>
          <Button
            color="inherit"
            component={RouterLink}
            to="/"
            startIcon={<DashboardIcon />}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/flows"
            startIcon={<TimelineIcon />}
          >
            Flows
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/anomalies"
            startIcon={<WarningIcon />}
          >
            Anomalies
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/model"
            startIcon={<PsychologyIcon />}
          >
            Model Status
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar; 