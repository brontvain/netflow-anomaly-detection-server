import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  CircularProgress,
  Button,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import axios from 'axios';
import { format } from 'date-fns';

const ModelStatus = () => {
  const [modelStatus, setModelStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [training, setTraining] = useState(false);

  const fetchModelStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/model/status');
      setModelStatus(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to fetch model status');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModelStatus();
    const interval = setInterval(fetchModelStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleTrain = async () => {
    setTraining(true);
    try {
      await axios.post('http://localhost:8000/model/train');
      await fetchModelStatus();
    } catch (err) {
      setError('Failed to train model');
    }
    setTraining(false);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Typography color="error" align="center">
        {error}
      </Typography>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Paper sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Model Status
            </Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={handleTrain}
              disabled={training}
            >
              {training ? 'Training...' : 'Train Model'}
            </Button>
          </Box>
          
          {modelStatus.status === 'no_active_model' ? (
            <Typography color="text.secondary">
              No active model found. Click "Train Model" to start training.
            </Typography>
          ) : (
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Model Information
                    </Typography>
                    <Typography>
                      Type: {modelStatus.model_type}
                    </Typography>
                    <Typography>
                      Last Trained: {format(new Date(modelStatus.last_trained), 'yyyy-MM-dd HH:mm:ss')}
                    </Typography>
                    <Typography>
                      Accuracy: {(modelStatus.accuracy * 100).toFixed(2)}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Model Parameters
                    </Typography>
                    <Typography component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(modelStatus.parameters, null, 2)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </Paper>
      </Grid>
    </Grid>
  );
};

export default ModelStatus; 