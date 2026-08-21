/*
===========================================================================

openQ4 arena campaign

Framework-side orchestration for the single-player arena ladder.  The actual
matches run in game_mp; this class owns campaign data, menu state, progression,
listen-server setup, bot population, and the authoritative result handoff.

===========================================================================
*/

#ifndef __ARENA_CAMPAIGN_H__
#define __ARENA_CAMPAIGN_H__

class idUserInterface;
class idCmdArgs;

struct arenaCampaignState_t;

class idArenaCampaign {
public:
							idArenaCampaign();
							~idArenaCampaign();

	void					Init();
	void					Shutdown();
	void					Frame();

	bool					IsGui( const idUserInterface *gui ) const;
	bool					IsActive() const;
	bool					NeedsCleanup() const;

	void					OpenSelector();
	void					OpenBrowser();
	void					CloseMenu();
	bool					HandleGuiCommand( const char *menuCommand );
	void					UpdateMainMenuGui( idUserInterface *gui );

	// Called by SpawnServer on both sides of a game-module reload. Returns
	// false only when an Arena launch was active but can no longer be prepared.
	bool					PrepareServer();
	void					PopulateBots();

	// Presents the shared "match aborted" report for a launch that failed
	// outside this class, before any listen server existed.
	void					ReportStartFailure();

	// Queues the narrow, strictly parsed game_mp -> framework result handoff.
	// Outcome values are 0 = loss, 1 = win, and 2 = draw.
	bool					QueueCompletion( const idCmdArgs &args );
	void					AbortMatch();

private:
	void					FinishPendingCompletion();
	bool					LoadCampaign();
	void					UpdateGui();
	void					StartSelectedMatch();
	void					CommitPendingMatch();
	void					QueueFailedCompletionCleanup();
	void					RetryResult();
	void					RequestResetProgress();
	void					CancelResetProgress();
	void					ResetProgress();
	void					DismissResult();
	void					ReturnToBrowserAfterStartFailure( int failure );

	arenaCampaignState_t *	state;

	friend void				ArenaCampaign_Finish_f( const idCmdArgs &args );
};

extern idArenaCampaign arenaCampaign;

#endif
