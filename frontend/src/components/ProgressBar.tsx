import { Box, LinearProgress, Typography } from '@mui/material'

interface ProgressBarProps {
  value: number
}

export default function ProgressBar({ value }: ProgressBarProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box sx={{ flex: 1, minWidth: 60 }}>
        <LinearProgress variant="determinate" value={value} />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 35 }}>
        {value}%
      </Typography>
    </Box>
  )
}
