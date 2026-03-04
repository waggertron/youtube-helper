import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Link,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  Tooltip,
  Typography,
} from '@mui/material'
import { useAuthStatus, useSync, useUploadSecret, useStartAuth, useResetDatabase } from '../hooks/useApi'
import { useQueryClient } from '@tanstack/react-query'
import ConfirmDialog from '../components/ConfirmDialog'

export default function Settings() {
  const { data } = useAuthStatus()
  const sync = useSync()
  const uploadSecret = useUploadSecret()
  const startAuth = useStartAuth()
  const resetDatabase = useResetDatabase()
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [resetDialogOpen, setResetDialogOpen] = useState(false)

  const authenticated = data?.authenticated ?? false
  const hasClientSecret = data?.has_client_secret ?? false
  const authSuccess = searchParams.get('auth') === 'success'
  const authError = searchParams.get('auth_error')

  // Clean up the query param and invalidate auth status when auth=success
  useEffect(() => {
    if (authSuccess) {
      qc.invalidateQueries({ queryKey: ['auth-status'] })
    }
  }, [authSuccess, qc])

  const activeStep = authenticated ? 2 : hasClientSecret ? 1 : 0

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadSecret.mutate(file)
    }
  }

  const handleAuthorize = () => {
    startAuth.mutate(undefined, {
      onSuccess: (data) => {
        window.open(data.auth_url, '_blank')
      },
    })
  }

  const handleDismissSuccess = () => {
    setSearchParams({})
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Authentication
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Connect your Google account to manage YouTube playlists. Follow the
            steps below to set up OAuth credentials.
          </Typography>

          {authSuccess && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={handleDismissSuccess}>
              Successfully authenticated! You can now manage your YouTube playlists.
            </Alert>
          )}

          {authError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setSearchParams({})}>
              Authorization failed: {authError === 'access_denied'
                ? 'Access was denied. Make sure your Google account is added as a test user in the OAuth consent screen.'
                : authError}
            </Alert>
          )}

          {authenticated ? (
            <Chip label="Authenticated" color="success" />
          ) : (
            <Stepper activeStep={activeStep} orientation="vertical">
              <Step>
                <StepLabel>Upload Client Secret</StepLabel>
                <StepContent>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    Upload your <code>client_secret.json</code> file from the Google Cloud Console:
                  </Typography>
                  <Box component="ol" sx={{ pl: 2, mb: 2, '& li': { mb: 0.5 } }}>
                    <li>
                      <Typography variant="body2">
                        Go to{' '}
                        <Link
                          href="https://console.cloud.google.com"
                          target="_blank"
                          rel="noopener"
                        >
                          console.cloud.google.com
                        </Link>
                      </Typography>
                    </li>
                    <li>
                      <Typography variant="body2">Create a new project (or select an existing one)</Typography>
                    </li>
                    <li>
                      <Typography variant="body2">
                        Enable the <strong>YouTube Data API v3</strong>
                      </Typography>
                    </li>
                    <li>
                      <Typography variant="body2">
                        Create OAuth 2.0 credentials (Desktop application)
                      </Typography>
                    </li>
                    <li>
                      <Typography variant="body2">Download the JSON file</Typography>
                    </li>
                  </Box>
                  <input
                    type="file"
                    accept=".json,application/json"
                    data-testid="secret-file-input"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                  />
                  <Button
                    variant="contained"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadSecret.isPending}
                  >
                    {uploadSecret.isPending ? 'Uploading...' : 'Choose File'}
                  </Button>
                  {uploadSecret.isError && (
                    <Alert severity="error" sx={{ mt: 1 }}>
                      {uploadSecret.error.message}
                    </Alert>
                  )}
                </StepContent>
              </Step>

              <Step>
                <StepLabel>Authorize</StepLabel>
                <StepContent>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    Click the button below to authorize this application with your Google account.
                    You will be redirected to Google to grant access.
                  </Typography>
                  <Button
                    variant="contained"
                    onClick={handleAuthorize}
                    disabled={startAuth.isPending}
                  >
                    {startAuth.isPending ? 'Starting...' : 'Authorize with Google'}
                  </Button>
                  {startAuth.isError && (
                    <Alert severity="error" sx={{ mt: 1 }}>
                      {startAuth.error.message}
                    </Alert>
                  )}
                </StepContent>
              </Step>
            </Stepper>
          )}
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Sync
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Sync pulls metadata for all your YouTube playlists into the local
            database. Run this periodically to keep your data up to date.
          </Typography>
          <Tooltip title="Sync all playlist metadata from YouTube into the local database. Uses API quota proportional to the number of playlists and videos.">
            <Button
              variant="contained"
              onClick={() => sync.mutate()}
              disabled={sync.isPending}
            >
              Sync Now
            </Button>
          </Tooltip>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Clear Database
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Remove all locally stored data including playlists, videos, and
            operation history. This does not delete anything on YouTube.
          </Typography>
          <Button
            variant="contained"
            color="error"
            onClick={() => setResetDialogOpen(true)}
            disabled={resetDatabase.isPending}
          >
            {resetDatabase.isPending ? 'Clearing...' : 'Clear Database'}
          </Button>
          {resetDatabase.isSuccess && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Database cleared successfully.
            </Alert>
          )}
          {resetDatabase.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {resetDatabase.error.message}
            </Alert>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={resetDialogOpen}
        title="Clear All Local Data"
        description="This will clear all local data including playlists, videos, liked status, and operation history. Nothing will be deleted on YouTube. You can re-sync your data afterwards."
        onConfirm={() => {
          setResetDialogOpen(false)
          resetDatabase.mutate()
        }}
        onCancel={() => setResetDialogOpen(false)}
      />
    </Box>
  )
}
