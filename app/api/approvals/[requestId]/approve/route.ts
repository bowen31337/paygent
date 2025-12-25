// app/api/approvals/[requestId]/approve/route.ts
// Resume workflow on approval for Vercel Workflow integration

import { NextRequest, NextResponse } from 'next/server';

interface ApprovalRequest {
  decision: 'approved' | 'rejected' | 'edited';
  editedArgs?: Record<string, any>;
}

/**
 * Resume workflow on approval decision
 * This endpoint is called when a user approves a pending approval request
 */
export async function POST(
  req: NextRequest,
  { params }: { params: { requestId: string } }
): Promise<NextResponse> {
  try {
    const { decision, editedArgs }: ApprovalRequest = await req.json();

    // Validate decision
    if (!['approved', 'rejected', 'edited'].includes(decision)) {
      return NextResponse.json(
        { success: false, error: 'Invalid decision' },
        { status: 400 }
      );
    }

    // Validate edited args if provided
    if (decision === 'edited' && (!editedArgs || Object.keys(editedArgs).length === 0)) {
      return NextResponse.json(
        { success: false, error: 'Edited args required for edit decision' },
        { status: 400 }
      );
    }

    // Resume the workflow hook with the decision
    try {
      // Import the approval hook from the workflow
      const { approvalHook } = await import('@/workflows/agent-payment-workflow');

      await approvalHook.resume(params.requestId, {
        decision,
        editedArgs
      });

      return NextResponse.json({
        success: true,
        message: 'Workflow resumed successfully',
        decision,
        requestId: params.requestId
      });

    } catch (hookError: any) {
      // If hook resume fails, it might be because the workflow has already timed out
      if (hookError.code === 'HOOK_NOT_FOUND') {
        return NextResponse.json({
          success: false,
          error: 'Approval request not found or already expired',
          requestId: params.requestId
        }, { status: 404 });
      } else if (hookError.code === 'HOOK_ALREADY_RESUMED') {
        return NextResponse.json({
          success: false,
          error: 'Approval request has already been processed',
          requestId: params.requestId
        }, { status: 409 });
      }

      throw hookError;
    }

  } catch (error: any) {
    console.error('Approval resume error:', error);

    return NextResponse.json({
      success: false,
      error: error.message || 'Failed to process approval',
      requestId: params.requestId
    }, { status: 500 });
  }
}

/**
 * Get approval request status
 * This endpoint allows checking the status of an approval request
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { requestId: string } }
): Promise<NextResponse> {
  try {
    // Import the approval hook to check status
    const { approvalHook } = await import('@/workflows/agent-payment-workflow');

    // Get hook status (this is a hypothetical API - actual implementation may vary)
    const status = await approvalHook.getStatus(params.requestId);

    return NextResponse.json({
      success: true,
      requestId: params.requestId,
      status: status.state, // pending, resumed, expired
      createdAt: status.createdAt,
      resumedAt: status.resumedAt,
      decision: status.decision
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message || 'Failed to get approval status',
      requestId: params.requestId
    }, { status: 500 });
  }
}

/**
 * Cancel approval request
 * This endpoint allows canceling a pending approval request
 */
export async function DELETE(
  req: NextRequest,
  { params }: { params: { requestId: string } }
): Promise<NextResponse> {
  try {
    // Import the approval hook
    const { approvalHook } = await import('@/workflows/agent-payment-workflow');

    // Cancel the hook
    await approvalHook.cancel(params.requestId);

    return NextResponse.json({
      success: true,
      message: 'Approval request canceled successfully',
      requestId: params.requestId
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message || 'Failed to cancel approval request',
      requestId: params.requestId
    }, { status: 500 });
  }
}