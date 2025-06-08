import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  CircularProgress,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import axios from 'axios';
import { format } from 'date-fns';

const Flows = () => {
  const [flows, setFlows] = useState([]);
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
      field: 'end_time',
      headerName: 'End Time',
      width: 180,
      valueFormatter: (params) => format(new Date(params.value), 'yyyy-MM-dd HH:mm:ss'),
    },
    { field: 'packets', headerName: 'Packets', width: 100 },
    { field: 'bytes', headerName: 'Bytes', width: 100 },
    {
      field: 'is_anomaly',
      headerName: 'Anomaly',
      width: 100,
      valueGetter: (params) => params.row.is_anomaly ? 'Yes' : 'No',
    },
  ];

  useEffect(() => {
    const fetchFlows = async () => {
      try {
        const response = await axios.get('http://localhost:8000/flows/', {
          params: {
            skip: paginationModel.page * paginationModel.pageSize,
            limit: paginationModel.pageSize,
          },
        });
        setFlows(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch flows');
        setLoading(false);
      }
    };

    fetchFlows();
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
    <Paper sx={{ height: 'calc(100vh - 200px)', width: '100%' }}>
      <DataGrid
        rows={flows}
        columns={columns}
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        pageSizeOptions={[25, 50, 100]}
        disableRowSelectionOnClick
      />
    </Paper>
  );
};

export default Flows; 