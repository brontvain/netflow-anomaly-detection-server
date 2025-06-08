import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  CircularProgress,
  Chip,
  Grid,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import axios from 'axios';
import { format } from 'date-fns';

const Anomalies = () => {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paginationModel, setPaginationModel] = useState({
    pageSize: 25,
    page: 0,
  });

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'src_ip', headerName: 'Source IP', width: 130 },
    { field: 'dst_ip', headerName: 'Destination IP', width: 130 },
    { field: 'src_port', headerName: 'Source Port', width: 100 },
    { field: 'dst_port', headerName: 'Destination Port', width: 100 },
    { field: 'protocol', headerName: 'Protocol', width: 100 },
    {
      field: 'start_time',
      headerName: 'Start Time',
      width: 180,
      valueFormatter: (params) => format(new Date(params.value), 'yyyy-MM-dd HH:mm:ss'),
    },
    {
      field: 'anomaly_type',
      headerName: 'Anomaly Type',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={params.value}
          color={
            params.value === 'unusual_port' ? 'warning' :
            params.value === 'unusual_protocol' ? 'error' :
            'default'
          }
        />
      ),
    },
    {
      field: 'anomaly_score',
      headerName: 'Anomaly Score',
      width: 130,
      valueFormatter: (params) => params.value.toFixed(3),
    },
  ];

  useEffect(() => {
    const fetchAnomalies = async () => {
      try {
        const response = await axios.get('http://localhost:8000/flows/anomalies', {
          params: {
            skip: paginationModel.page * paginationModel.pageSize,
            limit: paginationModel.pageSize,
          },
        });
        setAnomalies(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch anomalies');
        setLoading(false);
      }
    };

    fetchAnomalies();
    const interval = setInterval(fetchAnomalies, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [paginationModel]);

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
          <Typography variant="h6" gutterBottom>
            Detected Anomalies
          </Typography>
          <Box height="calc(100vh - 300px)">
            <DataGrid
              rows={anomalies}
              columns={columns}
              paginationModel={paginationModel}
              onPaginationModelChange={setPaginationModel}
              pageSizeOptions={[25, 50, 100]}
              disableRowSelectionOnClick
            />
          </Box>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default Anomalies; 