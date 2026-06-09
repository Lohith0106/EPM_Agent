# EPM Error Notebook (sample — replace with your own)

## FDMEE: "No periods were identified for loading data"
**Seen in:** file-based data load, ACTUALS rule
**Root cause:** the source period(s) in the file have no row in the *Application*
period mapping, or the Global period mapping is missing the calendar entry. Often a
new month was opened but never added to Period Mapping.
**Fix:**
1. Data Management > Setup > Period Mapping > Global Mapping — confirm the period exists.
2. Application Mapping for the target app — map the source period to the target.
3. Re-run; if still failing, check the POV period matches the file.
**Confirmed by:** load shows rows imported > 0 in Workbench.

## FDMEE: period mapping null end date
**Root cause:** a period row exists but the Target Period Month / end date column is blank.
**Fix:** edit the period row, set the period start/end and target period month, save.

## EPBCS: "No mapping found for source member X in dimension Y"
**Root cause:** the data load mapping for that dimension has no rule matching the source value.
**Fix:** Data Load Mapping > select the dimension > add an Explicit or Like (wildcard `*`)
rule mapping the source to a valid target member. Verify the target member exists and is level-0.

## ODI session failed + ORA-12899 (value too large for column)
**Root cause:** a source value is wider than the target/staging column — usually an
amount or a text member name exceeding the column length.
**Fix:** trim/clean the offending source value, or check the import format amount column
mapping. Inspect the ODI Operator session log for the exact column.

## IDCS OAuth2 AUTH-1163
**Root cause:** OAuth2 client/app config mismatch or expired token for the EPM REST call.
**Fix:** re-validate the IDCS confidential app scopes and client secret; regenerate the
token; confirm the role/grant on the EPM Cloud instance.
	1. Metadata Build - https://brovanture.com/loading-metadata-using-pbcs-data-management
	2. File based different loads - https://docs.oracle.com/en/cloud/saas/enterprise-performance-management-common/dmlpp/perform_a_basic_numeric_data_load.html
	3. Cube to Cube Integration - https://medium.com/@lohithreddypidimarla/cube-to-cube-integration-in-oracle-data-management-planning-cloud-84ed5eef2e8e
	4. Cloud to Cloud Integration - https://brovanture.com/oracle-cloud-epm-integrating-consolidation-and-close-with-planning
	5. HCM Direct Connection - https://medium.com/@lohithreddypidimarla/hcm-integration-to-workforce-acd0b0381a0c
	6. Integration Agent Set-up - https://medium.com/@lohithreddypidimarla/cube-to-cube-integration-in-oracle-data-management-planning-cloud-84ed5eef2e8e
	
	9. Oracle guide for Direct Connection - https://docs.oracle.com/en/cloud/saas/enterprise-performance-management-common/erpia/integrating_data_102xd66df14e.html 
	10. FDMEE Tables - https://docs.oracle.com/en/applications/enterprise-performance-management/11.2/dtmod/pdf/FinancialDataQualityManagement.pdf
	11. Refresh Members using Groovy - https://medium.com/@vigneshpt8/automating-data-exchange-target-application-refresh-members-in-oracle-epm-using-groovy-rest-api-925f9b0c5634
	12. Build missing members automatically in a single Parent:

	CASE
	    WHEN NOT EXISTS (
	        SELECT 1
	        FROM AIF_TARGET_APPL_MEMBERS W
	        WHERE W.MEMBER_NAME = ACCOUNT
	    ) 
	    THEN ACCOUNT
	    ELSE IGNORE
	END
