#ifndef _BSE_API_H_INC_
#define _BSE_API_H_INC_

#include "BSEInterface.h"

class idDecl;

typedef idDecl* (*BSE_AllocDeclEffect_t)(void);

rvBSEManager*				openQ4_GetIntegratedBSEManager( void );
rvDeclEffectEdit*			openQ4_GetIntegratedBSEDeclEffectEdit( void );
idDecl*						openQ4_AllocIntegratedBSEDeclEffect( void );
bool						openQ4_IsIntegratedBSEDeclEffect( const idDecl *decl );

extern BSE_AllocDeclEffect_t	bseAllocDeclEffect;

#endif // _BSE_API_H_INC_
