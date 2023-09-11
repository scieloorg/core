<?xml version='1.0' encoding='UTF-8'?>

<!-- 
  Simple transform of query results to export XML format
 -->
<xsl:stylesheet version='1.0'
    xmlns:xsl='http://www.w3.org/1999/XSL/Transform'
>

	<xsl:output media-type="text/xml; charset=UTF-8" encoding="UTF-8"/> 
  	<xsl:variable name="tag" select="response//str[@name = 'tag']/text()"/>

	<xsl:template match='/'>
		<doc-list>
			<xsl:apply-templates select="response/result/doc"/>
		</doc-list>
	</xsl:template>
  
	<xsl:template match="doc">		
    	<doc>
			<xsl:apply-templates/>
			<xsl:if test="$tag != ''">
				<field name="tag"><xsl:value-of select="$tag"/></field>
			</xsl:if>
    	</doc>
	</xsl:template>

	<xsl:template match="doc/*">
		<field name="{@name}">
          <xsl:value-of select="."/>
		</field>
	</xsl:template>

	<xsl:template match="doc/*[*]">
		<xsl:apply-templates>
			<xsl:with-param name="name"><xsl:value-of select="@name"/></xsl:with-param>
		</xsl:apply-templates>
	</xsl:template>

	
	<xsl:template match="doc/*/*">	
		<xsl:param name="name"/>
		<field name="{$name}">
          <xsl:value-of select="."/>
		</field>
	</xsl:template>

	<xsl:template match="doc/*[@name='score']"/>

	<xsl:template match="*"/>
  
</xsl:stylesheet>
